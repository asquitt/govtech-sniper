"""Settings proxy for Gemini service package.

This preserves import paths like ``app.services.gemini_service.settings`` that
tests and modules monkeypatch directly, while delegating reads to app config.
"""

from app.config import settings as _settings


def __getattr__(name: str):
    return getattr(_settings, name)
