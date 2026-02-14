from types import SimpleNamespace

import pytest

from app.services.gemini_service import GeminiService


class _QuotaFailModel:
    async def generate_content_async(self, prompt, generation_config=None):
        raise RuntimeError("Quota exceeded. Please retry in 5.0s.")


class _SuccessModel:
    async def generate_content_async(self, prompt, generation_config=None):
        return SimpleNamespace(
            text="Generated response",
            usage_metadata=SimpleNamespace(total_token_count=42),
        )


class TestGeminiService:
    def setup_method(self):
        GeminiService._quota_circuit_open_until = None

    def teardown_method(self):
        GeminiService._quota_circuit_open_until = None

    def test_extract_retry_after_seconds_parses_common_patterns(self):
        service = GeminiService(api_key=None)
        assert service._extract_retry_after_seconds(RuntimeError("retry in 12.5s")) == 12
        assert service._extract_retry_after_seconds(RuntimeError("retry_delay { seconds: 9 }")) == 9

    def test_open_quota_circuit_sets_remaining_window(self, monkeypatch):
        service = GeminiService(api_key=None)
        monkeypatch.setattr(
            "app.services.gemini_service.settings.gemini_rate_limit_cooldown_seconds",
            60,
        )
        monkeypatch.setattr(
            "app.services.gemini_service.settings.gemini_rate_limit_max_seconds",
            3600,
        )
        monkeypatch.setattr(
            "app.services.gemini_service.settings.gemini_rate_limit_daily_cooldown_seconds",
            1800,
        )

        opened = service._open_quota_circuit(
            retry_after_seconds=120,
            error_message="quota exceeded",
        )
        assert opened == 120
        remaining = service._get_remaining_quota_circuit_seconds()
        assert remaining is not None
        assert 1 <= remaining <= 120

    @pytest.mark.asyncio
    async def test_generate_with_fallback_uses_flash_model_when_primary_quota_limited(self):
        service = GeminiService(api_key=None)
        service.pro_model = _QuotaFailModel()
        service.pro_model_name = "gemini-2.5-pro"
        service.flash_model = _SuccessModel()
        service.flash_model_name = "gemini-1.5-flash"

        response, model_used = await service._generate_with_fallback(
            prompt="test prompt",
            generation_config=SimpleNamespace(),
            primary_model=service.pro_model,
            primary_model_name=service.pro_model_name,
        )

        assert response.text == "Generated response"
        assert model_used == "gemini-1.5-flash"

    def test_privacy_runtime_guarantees_reflect_runtime_flags(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.gemini_service.core.settings.gemini_data_usage_mode",
            "ephemeral_no_training",
        )
        monkeypatch.setattr(
            "app.services.gemini_service.core.settings.gemini_allow_provider_training",
            False,
        )
        monkeypatch.setattr(
            "app.services.gemini_service.core.settings.gemini_provider_retention_hours",
            0,
        )

        runtime = GeminiService.privacy_runtime_guarantees()
        assert runtime["processing_mode"] == "ephemeral_no_training"
        assert runtime["provider_training_allowed"] is False
        assert runtime["provider_retention_hours"] == 0
        assert runtime["no_training_enforced"] is True

    @pytest.mark.asyncio
    async def test_generate_with_fallback_fails_closed_when_training_allowed(self, monkeypatch):
        service = GeminiService(api_key=None)
        service.pro_model = _SuccessModel()
        service.pro_model_name = "gemini-1.5-pro"
        service.flash_model = None

        monkeypatch.setattr(
            "app.services.gemini_service.core.settings.gemini_allow_provider_training",
            True,
        )

        with pytest.raises(
            RuntimeError,
            match="training must remain disabled",
        ):
            await service._generate_with_fallback(
                prompt="test prompt",
                generation_config=SimpleNamespace(),
                primary_model=service.pro_model,
                primary_model_name=service.pro_model_name,
            )
