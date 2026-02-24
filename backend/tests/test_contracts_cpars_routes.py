"""
Integration tests for contracts/cpars.py:
  - GET    /contracts/{contract_id}/cpars
  - POST   /contracts/{contract_id}/cpars
  - GET    /contracts/{contract_id}/cpars/{cpars_id}/evidence
  - POST   /contracts/{contract_id}/cpars/{cpars_id}/evidence
  - DELETE /contracts/{contract_id}/cpars/{cpars_id}/evidence/{evidence_id}
"""

from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import ContractAward, CPARSEvidence, CPARSReview
from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.user import User
from app.services.auth_service import create_token_pair, hash_password

BASE = "/api/v1/contracts"


@pytest_asyncio.fixture
async def test_contract(db_session: AsyncSession, test_user: User) -> ContractAward:
    contract = ContractAward(
        user_id=test_user.id,
        contract_number="W912HV-24-C-0005",
        title="CPARS Test Contract",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest_asyncio.fixture
async def test_cpars(db_session: AsyncSession, test_contract: ContractAward) -> CPARSReview:
    review = CPARSReview(
        contract_id=test_contract.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 6, 30),
        overall_rating="Exceptional",
        notes="Strong performance.",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


@pytest_asyncio.fixture
async def test_kb_document(db_session: AsyncSession, test_user: User) -> KnowledgeBaseDocument:
    doc = KnowledgeBaseDocument(
        user_id=test_user.id,
        title="Performance Evidence Doc",
        document_type="past_performance",
        original_filename="evidence.pdf",
        file_path="/uploads/test/evidence.pdf",
        file_size_bytes=512000,
        mime_type="application/pdf",
        processing_status="ready",
        is_ready=True,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def test_evidence(
    db_session: AsyncSession,
    test_cpars: CPARSReview,
    test_kb_document: KnowledgeBaseDocument,
) -> CPARSEvidence:
    evidence = CPARSEvidence(
        cpars_id=test_cpars.id,
        document_id=test_kb_document.id,
        citation="Section 3.2 - On-time delivery metrics",
        notes="Key evidence for schedule rating.",
    )
    db_session.add(evidence)
    await db_session.commit()
    await db_session.refresh(evidence)
    return evidence


class TestListCPARS:
    """Tests for GET /contracts/{contract_id}/cpars."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/cpars")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/cpars", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_reviews(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
    ):
        response = await client.get(f"{BASE}/{test_contract.id}/cpars", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["overall_rating"] == "Exceptional"

    @pytest.mark.asyncio
    async def test_list_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/cpars", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
    ):
        other_user = User(
            email="other_cpars@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.get(f"{BASE}/{test_contract.id}/cpars", headers=headers)
        assert response.status_code == 404


class TestCreateCPARS:
    """Tests for POST /contracts/{contract_id}/cpars."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{BASE}/1/cpars", json={})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        payload = {
            "period_start": "2024-07-01",
            "period_end": "2024-12-31",
            "overall_rating": "Very Good",
            "notes": "Consistent delivery.",
        }
        response = await client.post(
            f"{BASE}/{test_contract.id}/cpars",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall_rating"] == "Very Good"
        assert data["contract_id"] == test_contract.id

    @pytest.mark.asyncio
    async def test_create_minimal(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.post(
            f"{BASE}/{test_contract.id}/cpars",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(f"{BASE}/99999/cpars", json={}, headers=auth_headers)
        assert response.status_code == 404


class TestListCPARSEvidence:
    """Tests for GET /contracts/{contract_id}/cpars/{cpars_id}/evidence."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get(f"{BASE}/1/cpars/1/evidence")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_evidence(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
        test_evidence: CPARSEvidence,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["citation"] == "Section 3.2 - On-time delivery metrics"
        assert data[0]["document_title"] == "Performance Evidence Doc"

    @pytest.mark.asyncio
    async def test_list_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"{BASE}/99999/cpars/1/evidence", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_cpars_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.get(
            f"{BASE}/{test_contract.id}/cpars/99999/evidence",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestAddCPARSEvidence:
    """Tests for POST /contracts/{contract_id}/cpars/{cpars_id}/evidence."""

    @pytest.mark.asyncio
    async def test_add_requires_auth(self, client: AsyncClient):
        response = await client.post(f"{BASE}/1/cpars/1/evidence", json={"document_id": 1})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
        test_kb_document: KnowledgeBaseDocument,
    ):
        payload = {
            "document_id": test_kb_document.id,
            "citation": "Appendix A - Quality Metrics",
            "notes": "Supporting quality rating.",
        }
        response = await client.post(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_kb_document.id
        assert data["citation"] == "Appendix A - Quality Metrics"
        assert data["document_title"] == "Performance Evidence Doc"

    @pytest.mark.asyncio
    async def test_add_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            f"{BASE}/99999/cpars/1/evidence",
            json={"document_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_cpars_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.post(
            f"{BASE}/{test_contract.id}/cpars/99999/evidence",
            json={"document_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_document_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
    ):
        payload = {"document_id": 99999}
        response = await client.post(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_missing_document_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
    ):
        response = await client.post(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_add_idor_document(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
    ):
        """Cannot link a document owned by another user."""
        other_user = User(
            email="other_cpars_doc@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        other_doc = KnowledgeBaseDocument(
            user_id=other_user.id,
            title="Other User Doc",
            document_type="past_performance",
            original_filename="other.pdf",
            file_path="/uploads/other/doc.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status="ready",
            is_ready=True,
        )
        db_session.add(other_doc)
        await db_session.commit()
        await db_session.refresh(other_doc)

        payload = {"document_id": other_doc.id}
        response = await client.post(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteCPARSEvidence:
    """Tests for DELETE /contracts/{contract_id}/cpars/{cpars_id}/evidence/{evidence_id}."""

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client: AsyncClient):
        response = await client.delete(f"{BASE}/1/cpars/1/evidence/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
        test_evidence: CPARSEvidence,
    ):
        response = await client.delete(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence/{test_evidence.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Evidence deleted"
        assert data["evidence_id"] == test_evidence.id

    @pytest.mark.asyncio
    async def test_delete_contract_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.delete(f"{BASE}/99999/cpars/1/evidence/1", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_cpars_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
    ):
        response = await client.delete(
            f"{BASE}/{test_contract.id}/cpars/99999/evidence/1",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_evidence_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
    ):
        response = await client.delete(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_idor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_contract: ContractAward,
        test_cpars: CPARSReview,
        test_evidence: CPARSEvidence,
    ):
        other_user = User(
            email="idor_cpars@example.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other User",
            company_name="Other Co",
            tier="professional",
            is_active=True,
            is_verified=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        tokens = create_token_pair(other_user.id, other_user.email, other_user.tier)
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        response = await client.delete(
            f"{BASE}/{test_contract.id}/cpars/{test_cpars.id}/evidence/{test_evidence.id}",
            headers=headers,
        )
        assert response.status_code == 404
