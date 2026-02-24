"""Unit tests for Salesforce service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.salesforce_service import SalesforceService, create_salesforce_service

VALID_CONFIG = {
    "instance_url": "https://test.salesforce.com",
    "client_id": "cl-id",
    "client_secret": "cl-secret",
    "username": "user@sf.com",
    "security_token": "tok-abc",
}


def _make_service() -> SalesforceService:
    return SalesforceService(**VALID_CONFIG)


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------
class TestCreateSalesforceService:
    def test_creates_with_valid_config(self):
        svc = create_salesforce_service(VALID_CONFIG)
        assert isinstance(svc, SalesforceService)
        assert svc.instance_url == "https://test.salesforce.com"

    def test_strips_trailing_slash_from_instance_url(self):
        config = {**VALID_CONFIG, "instance_url": "https://test.salesforce.com/"}
        svc = create_salesforce_service(config)
        assert svc.instance_url == "https://test.salesforce.com"

    def test_raises_on_missing_field(self):
        config = {k: v for k, v in VALID_CONFIG.items() if k != "username"}
        with pytest.raises(ValueError, match="username"):
            create_salesforce_service(config)

    def test_raises_on_empty_field(self):
        config = {**VALID_CONFIG, "client_secret": ""}
        with pytest.raises(ValueError, match="client_secret"):
            create_salesforce_service(config)

    def test_raises_on_empty_config(self):
        with pytest.raises(ValueError):
            create_salesforce_service({})


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------
class TestGetToken:
    @pytest.mark.asyncio
    async def test_fetches_oauth_token(self):
        svc = _make_service()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "sf-token",
            "instance_url": "https://na1.salesforce.com",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.salesforce_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            token = await svc._get_token()
            assert token == "sf-token"
            assert svc._token_instance_url == "https://na1.salesforce.com"

    @pytest.mark.asyncio
    async def test_caches_token(self):
        svc = _make_service()
        svc._access_token = "cached"
        token = await svc._get_token()
        assert token == "cached"


# ---------------------------------------------------------------------------
# Headers and base URL
# ---------------------------------------------------------------------------
class TestHeadersAndBaseUrl:
    def test_headers(self):
        svc = _make_service()
        headers = svc._headers("test-tok")
        assert headers["Authorization"] == "Bearer test-tok"
        assert headers["Content-Type"] == "application/json"

    def test_base_url_uses_token_instance(self):
        svc = _make_service()
        svc._token_instance_url = "https://na1.salesforce.com"
        assert "na1.salesforce.com" in svc._base_url()

    def test_base_url_falls_back_to_init_url(self):
        svc = _make_service()
        assert "test.salesforce.com" in svc._base_url()


# ---------------------------------------------------------------------------
# List opportunities
# ---------------------------------------------------------------------------
class TestListOpportunities:
    @pytest.mark.asyncio
    async def test_returns_records(self):
        svc = _make_service()
        svc._access_token = "tok"
        svc._token_instance_url = "https://na1.salesforce.com"

        records = [
            {"Id": "006abc", "Name": "Opp 1", "Amount": 50000},
            {"Id": "006def", "Name": "Opp 2", "Amount": 100000},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"records": records}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.salesforce_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.list_opportunities()
            assert len(result) == 2
            assert result[0]["Id"] == "006abc"


# ---------------------------------------------------------------------------
# Pull opportunities (normalized)
# ---------------------------------------------------------------------------
class TestPullOpportunities:
    @pytest.mark.asyncio
    async def test_normalizes_records(self):
        svc = _make_service()
        svc._access_token = "tok"
        svc._token_instance_url = "https://na1.salesforce.com"

        records = [
            {
                "Id": "006abc",
                "Name": "Opportunity A",
                "Amount": 75000,
                "StageName": "Proposal",
                "CloseDate": "2025-06-30",
            }
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"records": records}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.salesforce_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.pull_opportunities()
            assert len(result) == 1
            assert result[0]["sf_id"] == "006abc"
            assert result[0]["name"] == "Opportunity A"
            assert result[0]["amount"] == 75000
            assert result[0]["stage"] == "Proposal"


# ---------------------------------------------------------------------------
# Push opportunity
# ---------------------------------------------------------------------------
class TestPushOpportunity:
    @pytest.mark.asyncio
    async def test_creates_new_opportunity(self):
        svc = _make_service()
        svc._access_token = "tok"
        svc._token_instance_url = "https://na1.salesforce.com"

        # Create mock capture plan and RFP
        mock_plan = MagicMock()
        mock_plan.stage.value = "qualification"
        mock_plan.win_probability = 65

        mock_rfp = MagicMock()
        mock_rfp.title = "Test Opp"
        mock_rfp.id = 1
        mock_rfp.response_date = None

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "006new", "success": True}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"id":"006new","success":true}'

        with patch("app.services.salesforce_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.push_opportunity(mock_plan, mock_rfp)
            assert result["id"] == "006new"

    @pytest.mark.asyncio
    async def test_updates_existing_opportunity(self):
        svc = _make_service()
        svc._access_token = "tok"
        svc._token_instance_url = "https://na1.salesforce.com"

        mock_plan = MagicMock()
        mock_plan.stage.value = "proposal"
        mock_plan.win_probability = None

        mock_rfp = MagicMock()
        mock_rfp.title = "Update Opp"
        mock_rfp.id = 2
        mock_rfp.response_date = None

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b""
        mock_response.json.return_value = {}

        with patch("app.services.salesforce_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.patch.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await svc.push_opportunity(mock_plan, mock_rfp, sf_id="006exist")
            assert result == {"success": True}
