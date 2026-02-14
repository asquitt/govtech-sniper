"""
Bid Scenario Simulator Service
==============================
Deterministic stress-test simulation for bid/no-bid decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.models.capture import BidScorecard, BidScorecardRecommendation
from app.services.bid_decision_service import DEFAULT_BID_CRITERIA


@dataclass(slots=True)
class ScenarioAdjustment:
    criterion: str
    delta: float
    reason: str | None = None


@dataclass(slots=True)
class ScenarioDefinition:
    name: str
    adjustments: list[ScenarioAdjustment]
    notes: str | None = None


class BidScenarioService:
    """Deterministic bid/no-bid scenario simulator with explainable drivers."""

    CRITERION_RATIONALE_MAP = {
        "technical_capability": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Technical approach and capability",
        },
        "past_performance": {
            "far_reference": "FAR 15.305(a)(2)",
            "section_m_factor": "Past performance confidence",
        },
        "price_competitiveness": {
            "far_reference": "FAR 15.305(a)(1)",
            "section_m_factor": "Price/Cost realism and reasonableness",
        },
        "staffing_availability": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Management and staffing plan",
        },
        "clearance_requirements": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Security and compliance readiness",
        },
        "set_aside_eligibility": {
            "far_reference": "FAR 15.305(a)(2)",
            "section_m_factor": "Socioeconomic and eligibility compliance",
        },
        "relationship_with_agency": {
            "far_reference": "FAR 15.305(a)(2)",
            "section_m_factor": "Customer familiarity and execution confidence",
        },
        "competitive_landscape": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Competitive discriminators",
        },
        "geographic_fit": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Performance location feasibility",
        },
        "contract_vehicle_access": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Vehicle and eligibility constraints",
        },
        "teaming_strength": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Subcontractor/teaming capability",
        },
        "proposal_timeline": {
            "far_reference": "FAR 15.305(a)(3)",
            "section_m_factor": "Schedule and delivery feasibility",
        },
    }

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    @staticmethod
    def _normalize_criterion_name(name: str) -> str:
        return name.strip().lower()

    def _recommendation_for_score(self, score: float) -> BidScorecardRecommendation:
        if score >= 70:
            return BidScorecardRecommendation.BID
        if score <= 45:
            return BidScorecardRecommendation.NO_BID
        return BidScorecardRecommendation.CONDITIONAL

    def _decision_risk_level(self, score: float, confidence: float) -> tuple[str, float]:
        recommendation = self._recommendation_for_score(score)
        if recommendation == BidScorecardRecommendation.BID:
            boundary_distance = max(score - 70.0, 0.0) / 100.0
        elif recommendation == BidScorecardRecommendation.NO_BID:
            boundary_distance = max(45.0 - score, 0.0) / 100.0
        else:
            boundary_distance = min(abs(score - 70.0), abs(score - 45.0)) / 100.0

        risk_score = self._clamp(1.0 - ((0.6 * confidence) + (0.4 * boundary_distance)), 0.0, 1.0)
        if risk_score >= 0.66:
            return "high", risk_score
        if risk_score >= 0.33:
            return "medium", risk_score
        return "low", risk_score

    def _compute_weighted_score(self, criteria_scores: Sequence[dict[str, Any]]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for item in criteria_scores:
            weight = float(item.get("weight", 0.0))
            score = float(item.get("score", 0.0))
            weighted_sum += weight * score
            total_weight += weight
        if total_weight <= 0:
            return 0.0
        return weighted_sum / total_weight

    def _baseline_criteria(self, scorecard: BidScorecard) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        raw_criteria = scorecard.criteria_scores or []

        if raw_criteria:
            for item in raw_criteria:
                name = self._normalize_criterion_name(str(item.get("name", "")))
                if not name:
                    continue
                normalized.append(
                    {
                        "name": name,
                        "weight": float(item.get("weight", 0.0)),
                        "score": float(item.get("score", 0.0)),
                        "reasoning": item.get("reasoning"),
                    }
                )
            if normalized:
                return normalized

        # Fallback for legacy scorecards with missing criterion rows.
        fallback_score = float(scorecard.overall_score or 50.0)
        for criterion in DEFAULT_BID_CRITERIA:
            normalized.append(
                {
                    "name": self._normalize_criterion_name(criterion["name"]),
                    "weight": float(criterion["weight"]),
                    "score": fallback_score,
                    "reasoning": "Baseline imputed from overall score because criterion data was unavailable.",
                }
            )
        return normalized

    def default_scenarios(self, available_criteria: set[str]) -> list[ScenarioDefinition]:
        templates = [
            ScenarioDefinition(
                name="Aggressive Incumbent Response",
                notes="Incumbent undercuts pricing and leverages agency familiarity.",
                adjustments=[
                    ScenarioAdjustment(
                        "competitive_landscape", -22.0, "Incumbent pressure increased."
                    ),
                    ScenarioAdjustment("price_competitiveness", -18.0, "Likely price compression."),
                    ScenarioAdjustment(
                        "relationship_with_agency", -12.0, "Agency comfort favors incumbent."
                    ),
                ],
            ),
            ScenarioDefinition(
                name="Execution Capacity Shock",
                notes="Key staffing and schedule risks emerge during pursuit.",
                adjustments=[
                    ScenarioAdjustment(
                        "staffing_availability", -20.0, "Key roles become constrained."
                    ),
                    ScenarioAdjustment(
                        "proposal_timeline", -15.0, "Compressed submission timeline."
                    ),
                    ScenarioAdjustment(
                        "technical_capability", -10.0, "Coverage depth reduced by resourcing."
                    ),
                ],
            ),
            ScenarioDefinition(
                name="Compliance Surprise Amendment",
                notes="Late amendment introduces stricter eligibility and vehicle constraints.",
                adjustments=[
                    ScenarioAdjustment(
                        "clearance_requirements", -12.0, "Additional clearance burden."
                    ),
                    ScenarioAdjustment("set_aside_eligibility", -15.0, "Set-aside fit degrades."),
                    ScenarioAdjustment(
                        "contract_vehicle_access", -12.0, "Vehicle routing risk introduced."
                    ),
                ],
            ),
            ScenarioDefinition(
                name="Strategic Teaming Lift",
                notes="High-fit partner joins with relevant past performance and vehicle access.",
                adjustments=[
                    ScenarioAdjustment(
                        "teaming_strength", 20.0, "High-confidence partner committed."
                    ),
                    ScenarioAdjustment(
                        "past_performance", 12.0, "Partner fills past-performance gap."
                    ),
                    ScenarioAdjustment(
                        "contract_vehicle_access", 15.0, "Vehicle access risk reduced."
                    ),
                ],
            ),
        ]

        defaults: list[ScenarioDefinition] = []
        for template in templates:
            filtered = [
                adjustment
                for adjustment in template.adjustments
                if self._normalize_criterion_name(adjustment.criterion) in available_criteria
            ]
            if filtered:
                defaults.append(
                    ScenarioDefinition(
                        name=template.name,
                        notes=template.notes,
                        adjustments=filtered,
                    )
                )
        return defaults

    def simulate(
        self,
        scorecard: BidScorecard,
        scenarios: Sequence[ScenarioDefinition] | None = None,
    ) -> dict[str, Any]:
        baseline_criteria = self._baseline_criteria(scorecard)
        baseline_score = self._compute_weighted_score(baseline_criteria)
        baseline_recommendation = scorecard.recommendation or self._recommendation_for_score(
            baseline_score
        )
        baseline_confidence = self._clamp(float(scorecard.confidence or 0.6), 0.05, 0.95)
        total_weight = sum(float(item["weight"]) for item in baseline_criteria) or 1.0

        criteria_index = {
            self._normalize_criterion_name(item["name"]): item for item in baseline_criteria
        }
        scenario_defs = list(scenarios or self.default_scenarios(set(criteria_index.keys())))

        scenario_results: list[dict[str, Any]] = []
        for scenario in scenario_defs:
            deltas = {
                self._normalize_criterion_name(adjustment.criterion): adjustment
                for adjustment in scenario.adjustments
            }

            adjusted_rows: list[dict[str, Any]] = []
            stress_numerator = 0.0
            for criterion in baseline_criteria:
                name = self._normalize_criterion_name(str(criterion["name"]))
                weight = float(criterion["weight"])
                baseline = float(criterion["score"])
                adjustment = deltas.get(name)
                delta = float(adjustment.delta) if adjustment else 0.0
                scenario_score = self._clamp(baseline + delta, 0.0, 100.0)
                weighted_impact = (scenario_score - baseline) * (weight / 100.0)
                rationale_meta = self.CRITERION_RATIONALE_MAP.get(
                    name,
                    {
                        "far_reference": "FAR 15.305(a)(3)",
                        "section_m_factor": "Technical/management discriminator",
                    },
                )

                adjusted_rows.append(
                    {
                        "name": name,
                        "weight": weight,
                        "baseline_score": baseline,
                        "scenario_score": scenario_score,
                        "delta": scenario_score - baseline,
                        "weighted_impact": weighted_impact,
                        "reason": adjustment.reason if adjustment else None,
                        "far_reference": rationale_meta["far_reference"],
                        "section_m_factor": rationale_meta["section_m_factor"],
                    }
                )
                stress_numerator += abs(scenario_score - baseline) * weight

            scenario_score = self._compute_weighted_score(
                [{"weight": row["weight"], "score": row["scenario_score"]} for row in adjusted_rows]
            )
            scenario_recommendation = self._recommendation_for_score(scenario_score)
            recommendation_changed = scenario_recommendation != baseline_recommendation

            stress_magnitude = self._clamp(stress_numerator / (100.0 * total_weight), 0.0, 1.0)
            score_shift = abs(scenario_score - baseline_score) / 100.0
            stability_bonus = 0.08 if not recommendation_changed else -0.07
            calibrated_confidence = self._clamp(
                baseline_confidence
                + stability_bonus
                - (0.45 * stress_magnitude)
                - (0.25 * score_shift),
                0.05,
                0.95,
            )
            decision_risk, risk_score = self._decision_risk_level(
                scenario_score, calibrated_confidence
            )

            positive_drivers = sorted(
                [row for row in adjusted_rows if row["weighted_impact"] > 0],
                key=lambda row: row["weighted_impact"],
                reverse=True,
            )[:3]
            negative_drivers = sorted(
                [row for row in adjusted_rows if row["weighted_impact"] < 0],
                key=lambda row: row["weighted_impact"],
            )[:3]

            ignored_adjustments = [
                {
                    "criterion": adjustment.criterion,
                    "delta": adjustment.delta,
                    "reason": adjustment.reason,
                }
                for adjustment in scenario.adjustments
                if self._normalize_criterion_name(adjustment.criterion) not in criteria_index
            ]

            top_rationale_rows = sorted(
                adjusted_rows,
                key=lambda row: abs(row["weighted_impact"]),
                reverse=True,
            )[:3]
            scoring_rationale = {
                "method": "Weighted-factor simulation aligned to FAR 15.305 and Section M factors",
                "dominant_factors": [
                    {
                        "criterion": row["name"],
                        "weighted_impact": row["weighted_impact"],
                        "far_reference": row["far_reference"],
                        "section_m_factor": row["section_m_factor"],
                    }
                    for row in top_rationale_rows
                ],
            }

            scenario_results.append(
                {
                    "name": scenario.name,
                    "notes": scenario.notes,
                    "overall_score": round(scenario_score, 2),
                    "recommendation": scenario_recommendation.value,
                    "confidence": round(calibrated_confidence, 3),
                    "decision_risk": decision_risk,
                    "risk_score": round(risk_score, 3),
                    "recommendation_changed": recommendation_changed,
                    "criteria_scores": adjusted_rows,
                    "driver_summary": {
                        "positive": positive_drivers,
                        "negative": negative_drivers,
                    },
                    "scoring_rationale": scoring_rationale,
                    "ignored_adjustments": ignored_adjustments,
                }
            )

        return {
            "rfp_id": scorecard.rfp_id,
            "baseline": {
                "scorecard_id": scorecard.id,
                "overall_score": round(baseline_score, 2),
                "recommendation": baseline_recommendation.value,
                "confidence": round(baseline_confidence, 3),
                "criteria_scores": baseline_criteria,
                "scoring_method": "Weighted-factor simulation aligned to FAR 15.305 and Section M factors",
            },
            "scenarios": scenario_results,
        }
