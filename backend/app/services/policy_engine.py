"""
Policy Decision Engine for CUI/FCI data access control.

Evaluates whether a user action (export, share, download) should be
allowed, denied, or require step-up authentication based on the
entity's data classification and the user's role.
"""

from __future__ import annotations

from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class PolicyAction(str, Enum):
    """Actions that are policy-evaluated."""

    EXPORT = "export"
    SHARE = "share"
    DOWNLOAD = "download"
    DELETE = "delete"


class PolicyDecision(str, Enum):
    """Result of a policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    STEP_UP = "step_up"


class PolicyResult:
    """Structured policy evaluation result with audit metadata."""

    def __init__(
        self,
        decision: PolicyDecision,
        reason: str,
        action: PolicyAction,
        classification: str,
        user_role: str,
    ):
        self.decision = decision
        self.reason = reason
        self.action = action
        self.classification = classification
        self.user_role = user_role

    def is_allowed(self) -> bool:
        return self.decision == PolicyDecision.ALLOW

    def to_audit_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "action": self.action.value,
            "classification": self.classification,
            "user_role": self.user_role,
        }


# Policy rules: (classification, action) -> required minimum role or decision
# Roles ranked: viewer < editor < admin < owner
ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2, "owner": 3}

# CUI requires admin+ for export/share, step-up for download
# FCI requires editor+ for export/share
# Internal/public: allow all
POLICY_RULES: dict[tuple[str, PolicyAction], tuple[PolicyDecision, str, int]] = {
    # CUI rules
    ("cui", PolicyAction.EXPORT): (PolicyDecision.STEP_UP, "CUI export requires step-up auth", 2),
    ("cui", PolicyAction.SHARE): (PolicyDecision.DENY, "CUI sharing requires admin approval", 2),
    ("cui", PolicyAction.DOWNLOAD): (
        PolicyDecision.STEP_UP,
        "CUI download requires step-up auth",
        1,
    ),
    ("cui", PolicyAction.DELETE): (PolicyDecision.DENY, "CUI deletion requires owner", 3),
    # FCI rules
    ("fci", PolicyAction.EXPORT): (PolicyDecision.ALLOW, "FCI export allowed for editors+", 1),
    ("fci", PolicyAction.SHARE): (PolicyDecision.ALLOW, "FCI sharing allowed for editors+", 1),
    ("fci", PolicyAction.DOWNLOAD): (PolicyDecision.ALLOW, "FCI download allowed", 0),
    ("fci", PolicyAction.DELETE): (PolicyDecision.ALLOW, "FCI deletion allowed for admins+", 2),
    # Internal rules
    ("internal", PolicyAction.EXPORT): (PolicyDecision.ALLOW, "Internal export allowed", 0),
    ("internal", PolicyAction.SHARE): (PolicyDecision.ALLOW, "Internal sharing allowed", 0),
    ("internal", PolicyAction.DOWNLOAD): (PolicyDecision.ALLOW, "Internal download allowed", 0),
    ("internal", PolicyAction.DELETE): (
        PolicyDecision.ALLOW,
        "Internal deletion allowed for editors+",
        1,
    ),
    # Public rules
    ("public", PolicyAction.EXPORT): (PolicyDecision.ALLOW, "Public export allowed", 0),
    ("public", PolicyAction.SHARE): (PolicyDecision.ALLOW, "Public sharing allowed", 0),
    ("public", PolicyAction.DOWNLOAD): (PolicyDecision.ALLOW, "Public download allowed", 0),
    ("public", PolicyAction.DELETE): (PolicyDecision.ALLOW, "Public deletion allowed", 0),
}


def evaluate(
    action: PolicyAction,
    classification: str,
    user_role: str,
) -> PolicyResult:
    """
    Evaluate a policy decision for the given action, classification, and role.

    Args:
        action: The action being attempted (export, share, download, delete)
        classification: Data classification level (public, internal, fci, cui)
        user_role: User's role (viewer, editor, admin, owner)

    Returns:
        PolicyResult with decision, reason, and audit metadata
    """
    classification = classification.lower()
    user_role = user_role.lower()

    key = (classification, action)
    rule = POLICY_RULES.get(key)

    if rule is None:
        logger.warning(
            "policy_rule_missing",
            classification=classification,
            action=action.value,
            user_role=user_role,
        )
        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason=f"No policy rule for {classification}/{action.value}",
            action=action,
            classification=classification,
            user_role=user_role,
        )

    decision, reason, min_role_rank = rule
    actual_rank = ROLE_RANK.get(user_role, 0)

    # If user doesn't meet minimum role, deny regardless
    if actual_rank < min_role_rank:
        logger.info(
            "policy_denied_insufficient_role",
            action=action.value,
            classification=classification,
            user_role=user_role,
            required_rank=min_role_rank,
        )
        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason=f"Insufficient role: {user_role} (need rank {min_role_rank}+)",
            action=action,
            classification=classification,
            user_role=user_role,
        )

    logger.info(
        "policy_evaluated",
        decision=decision.value,
        action=action.value,
        classification=classification,
        user_role=user_role,
    )

    return PolicyResult(
        decision=decision,
        reason=reason,
        action=action,
        classification=classification,
        user_role=user_role,
    )
