"""
Policy Engine Unit Tests
=========================
Tests for CUI/FCI data access control decisions.
"""

from app.services.policy_engine import (
    PolicyAction,
    PolicyDecision,
    PolicyResult,
    evaluate,
)

# =============================================================================
# CUI Classification Tests
# =============================================================================


class TestCUIPolicy:
    def test_cui_export_step_up_for_admin(self):
        result = evaluate(PolicyAction.EXPORT, "cui", "admin")
        assert result.decision == PolicyDecision.STEP_UP

    def test_cui_export_denied_for_editor(self):
        result = evaluate(PolicyAction.EXPORT, "cui", "editor")
        assert result.decision == PolicyDecision.DENY

    def test_cui_share_denied_for_admin(self):
        result = evaluate(PolicyAction.SHARE, "cui", "admin")
        assert result.decision == PolicyDecision.DENY

    def test_cui_download_step_up_for_editor(self):
        result = evaluate(PolicyAction.DOWNLOAD, "cui", "editor")
        assert result.decision == PolicyDecision.STEP_UP

    def test_cui_download_denied_for_viewer(self):
        result = evaluate(PolicyAction.DOWNLOAD, "cui", "viewer")
        assert result.decision == PolicyDecision.DENY

    def test_cui_delete_denied_for_admin(self):
        result = evaluate(PolicyAction.DELETE, "cui", "admin")
        assert result.decision == PolicyDecision.DENY

    def test_cui_delete_denied_for_owner(self):
        result = evaluate(PolicyAction.DELETE, "cui", "owner")
        assert result.decision == PolicyDecision.DENY


# =============================================================================
# FCI Classification Tests
# =============================================================================


class TestFCIPolicy:
    def test_fci_export_allowed_for_editor(self):
        result = evaluate(PolicyAction.EXPORT, "fci", "editor")
        assert result.decision == PolicyDecision.ALLOW

    def test_fci_export_denied_for_viewer(self):
        result = evaluate(PolicyAction.EXPORT, "fci", "viewer")
        assert result.decision == PolicyDecision.DENY

    def test_fci_download_allowed_for_viewer(self):
        result = evaluate(PolicyAction.DOWNLOAD, "fci", "viewer")
        assert result.decision == PolicyDecision.ALLOW

    def test_fci_delete_allowed_for_admin(self):
        result = evaluate(PolicyAction.DELETE, "fci", "admin")
        assert result.decision == PolicyDecision.ALLOW

    def test_fci_delete_denied_for_editor(self):
        result = evaluate(PolicyAction.DELETE, "fci", "editor")
        assert result.decision == PolicyDecision.DENY


# =============================================================================
# Public/Internal Classification Tests
# =============================================================================


class TestPublicInternalPolicy:
    def test_public_export_allowed_for_viewer(self):
        result = evaluate(PolicyAction.EXPORT, "public", "viewer")
        assert result.decision == PolicyDecision.ALLOW

    def test_public_delete_allowed_for_viewer(self):
        result = evaluate(PolicyAction.DELETE, "public", "viewer")
        assert result.decision == PolicyDecision.ALLOW

    def test_internal_export_allowed_for_viewer(self):
        result = evaluate(PolicyAction.EXPORT, "internal", "viewer")
        assert result.decision == PolicyDecision.ALLOW

    def test_internal_delete_denied_for_viewer(self):
        result = evaluate(PolicyAction.DELETE, "internal", "viewer")
        assert result.decision == PolicyDecision.DENY

    def test_internal_delete_allowed_for_editor(self):
        result = evaluate(PolicyAction.DELETE, "internal", "editor")
        assert result.decision == PolicyDecision.ALLOW


# =============================================================================
# Edge Cases
# =============================================================================


class TestPolicyEdgeCases:
    def test_unknown_classification_denied(self):
        result = evaluate(PolicyAction.EXPORT, "top_secret", "owner")
        assert result.decision == PolicyDecision.DENY
        assert "No policy rule" in result.reason

    def test_case_insensitive_classification(self):
        result = evaluate(PolicyAction.DOWNLOAD, "FCI", "editor")
        assert result.decision == PolicyDecision.ALLOW

    def test_case_insensitive_role(self):
        result = evaluate(PolicyAction.DOWNLOAD, "fci", "EDITOR")
        assert result.decision == PolicyDecision.ALLOW


# =============================================================================
# PolicyResult Methods
# =============================================================================


class TestPolicyResult:
    def test_is_allowed_true(self):
        r = PolicyResult(PolicyDecision.ALLOW, "ok", PolicyAction.EXPORT, "public", "viewer")
        assert r.is_allowed() is True

    def test_is_allowed_false_for_deny(self):
        r = PolicyResult(PolicyDecision.DENY, "no", PolicyAction.EXPORT, "cui", "viewer")
        assert r.is_allowed() is False

    def test_is_allowed_false_for_step_up(self):
        r = PolicyResult(PolicyDecision.STEP_UP, "mfa", PolicyAction.EXPORT, "cui", "admin")
        assert r.is_allowed() is False

    def test_to_audit_dict(self):
        r = PolicyResult(PolicyDecision.ALLOW, "ok", PolicyAction.DOWNLOAD, "fci", "editor")
        d = r.to_audit_dict()
        assert d["decision"] == "allow"
        assert d["action"] == "download"
        assert d["classification"] == "fci"
        assert d["user_role"] == "editor"
