"""
Integration tests for benchmark.py routes:
  - GET  /api/v1/benchmark/scenarios
  - POST /api/v1/benchmark/score
  - POST /api/v1/benchmark/score-batch
"""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# GET /api/v1/benchmark/scenarios
# ---------------------------------------------------------------------------


class TestListScenarios:
    """GET /api/v1/benchmark/scenarios"""

    @pytest.mark.asyncio
    async def test_returns_scenarios_without_auth(self, client: AsyncClient):
        """Benchmark scenarios use get_current_user_optional so no auth needed."""
        response = await client.get("/api/v1/benchmark/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "rfp_type" in data[0]
            assert "title" in data[0]
            assert "sections" in data[0]
            assert "key_requirements" in data[0]

    @pytest.mark.asyncio
    async def test_returns_scenarios_with_auth(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/benchmark/scenarios", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# POST /api/v1/benchmark/score
# ---------------------------------------------------------------------------


class TestScoreSection:
    """POST /api/v1/benchmark/score"""

    @pytest.mark.asyncio
    async def test_score_section(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/benchmark/score",
            json={
                "section_name": "Technical Approach",
                "section_text": (
                    "Our team has extensive experience delivering cybersecurity "
                    "solutions for federal agencies. We propose a comprehensive "
                    "approach that leverages automation and machine learning to "
                    "detect threats in real-time. Our past performance includes "
                    "3 similar contracts with DOD agencies."
                ),
                "requirements": [
                    "Describe cybersecurity approach",
                    "Include past performance references",
                    "Detail automation capabilities",
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "section_name" in data
        assert "compliance_coverage" in data
        assert "specificity" in data
        assert "overall" in data
        assert "is_pink_team_ready" in data
        assert isinstance(data["overall"], float)

    @pytest.mark.asyncio
    async def test_score_section_empty_text(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/benchmark/score",
            json={
                "section_name": "Test",
                "section_text": "",
                "requirements": ["req1"],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_score_section_empty_requirements(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/benchmark/score",
            json={
                "section_name": "Test",
                "section_text": "Some content here",
                "requirements": [],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_score_section_missing_fields(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/benchmark/score",
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/benchmark/score-batch
# ---------------------------------------------------------------------------


class TestScoreBatch:
    """POST /api/v1/benchmark/score-batch"""

    @pytest.mark.asyncio
    async def test_score_batch(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/benchmark/score-batch?rfp_type=it_services",
            json=[
                {
                    "section_name": "Technical Approach",
                    "section_text": (
                        "We propose a modern IT infrastructure solution "
                        "using cloud-native architecture with zero-trust security."
                    ),
                    "requirements": [
                        "Describe IT infrastructure approach",
                        "Include security architecture",
                    ],
                },
                {
                    "section_name": "Management Approach",
                    "section_text": (
                        "Our project management methodology follows PMI standards "
                        "with Agile delivery and continuous integration."
                    ),
                    "requirements": [
                        "Describe project management methodology",
                    ],
                },
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert "rfp_type" in data
        assert "sections" in data
        assert "overall_score" in data
        assert "pink_team_ready" in data
        assert "recommendations" in data
        assert len(data["sections"]) == 2

    @pytest.mark.asyncio
    async def test_score_batch_empty_sections(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/benchmark/score-batch?rfp_type=test",
            json=[],
        )
        # Empty list is valid but produces 0 overall
        assert response.status_code == 200
        assert response.json()["overall_score"] == 0
