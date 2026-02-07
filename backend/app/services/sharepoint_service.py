"""
RFP Sniper - SharePoint Integration Service
=============================================
Microsoft Graph API client for SharePoint file operations.
Requires IntegrationConfig with provider=sharepoint and config containing:
  tenant_id, client_id, client_secret, site_id, drive_id
"""

import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class SharePointService:
    """Thin wrapper around Microsoft Graph API for SharePoint file operations."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        site_id: str,
        drive_id: str,
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_id = site_id
        self.drive_id = drive_id
        self._token: str | None = None

    async def _get_token(self) -> str:
        """Acquire OAuth2 client credentials token from Azure AD."""
        if self._token:
            return self._token

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def list_files(self, folder_path: str = "/") -> list[dict]:
        """List files and folders at a given path."""
        token = await self._get_token()
        path_segment = (
            f"root:/{folder_path.strip('/')}:/children"
            if folder_path.strip("/")
            else "root/children"
        )
        url = f"{GRAPH_BASE}/drives/{self.drive_id}/{path_segment}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(token))
            resp.raise_for_status()
            items = resp.json().get("value", [])
            return [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "is_folder": "folder" in item,
                    "size": item.get("size", 0),
                    "last_modified": item.get("lastModifiedDateTime"),
                    "web_url": item.get("webUrl"),
                }
                for item in items
            ]

    async def download_file(self, file_id: str) -> bytes:
        """Download a file by its Drive item ID."""
        token = await self._get_token()
        url = f"{GRAPH_BASE}/drives/{self.drive_id}/items/{file_id}/content"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(token), follow_redirects=True)
            resp.raise_for_status()
            return resp.content

    async def upload_file(self, folder_path: str, name: str, content: bytes) -> dict:
        """Upload a file to a specific folder."""
        token = await self._get_token()
        path = f"{folder_path.strip('/')}/{name}"
        url = f"{GRAPH_BASE}/drives/{self.drive_id}/root:/{path}:/content"
        headers = {**self._headers(token), "Content-Type": "application/octet-stream"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(url, headers=headers, content=content)
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": data["id"],
                "name": data["name"],
                "web_url": data.get("webUrl"),
                "size": data.get("size", 0),
            }


def create_sharepoint_service(config: dict) -> SharePointService:
    """Factory: build SharePointService from IntegrationConfig.config dict."""
    required = ["tenant_id", "client_id", "client_secret", "site_id", "drive_id"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f"Missing SharePoint config keys: {missing}")
    return SharePointService(**{k: config[k] for k in required})
