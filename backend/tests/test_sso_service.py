"""
SSO Service Unit Tests
========================
Tests for pure helper functions: decode_id_token_claims, _map_groups_to_role.
Network and DB functions are not tested here.
"""

import base64
import json

from app.models.organization import OrgRole
from app.services.sso_service import _map_groups_to_role, decode_id_token_claims

# =============================================================================
# decode_id_token_claims
# =============================================================================


def _build_jwt(payload: dict) -> str:
    """Build a fake JWT with the given payload (no signature verification)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    sig = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=")
    return f"{header.decode()}.{body.decode()}.{sig.decode()}"


class TestDecodeIdTokenClaims:
    def test_valid_token_decodes_payload(self):
        payload = {"sub": "user123", "email": "test@example.com", "name": "Test User"}
        token = _build_jwt(payload)
        result = decode_id_token_claims(token)
        assert result["sub"] == "user123"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"

    def test_token_with_groups(self):
        payload = {"sub": "u1", "groups": ["admins", "developers"]}
        token = _build_jwt(payload)
        result = decode_id_token_claims(token)
        assert result["groups"] == ["admins", "developers"]

    def test_empty_string_returns_empty_dict(self):
        assert decode_id_token_claims("") == {}

    def test_single_part_returns_empty_dict(self):
        assert decode_id_token_claims("only-one-part") == {}

    def test_two_parts_returns_empty_dict(self):
        assert decode_id_token_claims("part1.part2") == {}

    def test_four_parts_returns_empty_dict(self):
        assert decode_id_token_claims("a.b.c.d") == {}

    def test_invalid_base64_returns_empty_dict(self):
        assert decode_id_token_claims("header.!!!invalid!!!.signature") == {}

    def test_invalid_json_returns_empty_dict(self):
        # Valid base64 but not JSON
        not_json = base64.urlsafe_b64encode(b"not-json").rstrip(b"=").decode()
        token = f"header.{not_json}.signature"
        assert decode_id_token_claims(token) == {}

    def test_padding_handled_correctly(self):
        """JWT base64 strips padding; decode_id_token_claims must re-add it."""
        payload = {"sub": "abc", "email": "a@b.com", "iat": 1234567890}
        token = _build_jwt(payload)
        result = decode_id_token_claims(token)
        assert result["sub"] == "abc"
        assert result["iat"] == 1234567890


# =============================================================================
# _map_groups_to_role
# =============================================================================


class TestMapGroupsToRole:
    def test_owner_group(self):
        assert _map_groups_to_role(["owner"]) == OrgRole.OWNER

    def test_owners_group(self):
        assert _map_groups_to_role(["owners"]) == OrgRole.OWNER

    def test_org_owner_group(self):
        assert _map_groups_to_role(["org-owner"]) == OrgRole.OWNER

    def test_admin_group(self):
        assert _map_groups_to_role(["admin"]) == OrgRole.ADMIN

    def test_admins_group(self):
        assert _map_groups_to_role(["admins"]) == OrgRole.ADMIN

    def test_org_admin_group(self):
        assert _map_groups_to_role(["org-admin"]) == OrgRole.ADMIN

    def test_administrators_group(self):
        assert _map_groups_to_role(["administrators"]) == OrgRole.ADMIN

    def test_viewer_group(self):
        assert _map_groups_to_role(["viewer"]) == OrgRole.VIEWER

    def test_viewers_group(self):
        assert _map_groups_to_role(["viewers"]) == OrgRole.VIEWER

    def test_read_only_group(self):
        assert _map_groups_to_role(["read-only"]) == OrgRole.VIEWER

    def test_default_is_member(self):
        assert _map_groups_to_role(["developers"]) == OrgRole.MEMBER

    def test_empty_groups_returns_member(self):
        assert _map_groups_to_role([]) == OrgRole.MEMBER

    def test_owner_takes_priority_over_admin(self):
        assert _map_groups_to_role(["admin", "owner"]) == OrgRole.OWNER

    def test_admin_takes_priority_over_viewer(self):
        assert _map_groups_to_role(["viewer", "admin"]) == OrgRole.ADMIN

    def test_case_insensitive(self):
        assert _map_groups_to_role(["OWNER"]) == OrgRole.OWNER
        assert _map_groups_to_role(["Admin"]) == OrgRole.ADMIN
        assert _map_groups_to_role(["VIEWER"]) == OrgRole.VIEWER

    def test_mixed_case_groups(self):
        assert _map_groups_to_role(["Org-Admin"]) == OrgRole.ADMIN
