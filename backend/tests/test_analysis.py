"""
RFP Sniper - Analysis Tests
===========================
Tests for compliance matrix editing endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.rfp import ComplianceMatrix, RFP
from app.models.user import User


@pytest.mark.asyncio
async def test_compliance_matrix_editing(
    client: AsyncClient,
    db_session,
    test_user: User,
    test_rfp: RFP,
):
    # Seed compliance matrix
    matrix = ComplianceMatrix(
        rfp_id=test_rfp.id,
        requirements=[
            {
                "id": "REQ-001",
                "section": "L.1",
                "requirement_text": "Provide a technical approach.",
                "importance": "mandatory",
                "category": "Technical",
                "page_reference": 3,
                "keywords": ["approach"],
                "is_addressed": False,
                "notes": None,
            }
        ],
        total_requirements=1,
        mandatory_count=1,
        addressed_count=0,
    )
    db_session.add(matrix)
    await db_session.commit()

    # Add a new requirement
    response = await client.post(
        f"/api/v1/analyze/{test_rfp.id}/matrix",
        json={
            "section": "M.2",
            "requirement_text": "Provide past performance.",
            "importance": "evaluated",
            "category": "Past Performance",
            "page_reference": 7,
            "keywords": ["past", "performance"],
            "is_addressed": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_requirements"] == 2

    # Update requirement
    response = await client.patch(
        f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001",
        json={"notes": "Need SME input", "is_addressed": True},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["addressed_count"] == 1

    # Delete requirement
    response = await client.delete(
        f"/api/v1/analyze/{test_rfp.id}/matrix/REQ-001"
    )
    assert response.status_code == 200
