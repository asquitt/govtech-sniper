"""
RFP Sniper - Configuration Management
=====================================
Uses Pydantic Settings for type-safe environment variable handling.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All sensitive values should be set via environment variables, not hardcoded.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = "RFP Sniper"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False)
    secret_key: str = Field(default="CHANGE_ME_IN_PRODUCTION")

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://rfpsniper:rfpsniper_secret@localhost:5432/rfpsniper_db"
    )

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # -------------------------------------------------------------------------
    # External APIs
    # -------------------------------------------------------------------------
    sam_gov_api_key: Optional[str] = Field(default=None)
    sam_gov_base_url: str = Field(
        default="https://api.sam.gov/prod/opportunities/v2/search"
    )
    sam_download_attachments: bool = Field(default=True)
    sam_max_attachments: int = Field(default=10, ge=1, le=50)
    sam_circuit_breaker_enabled: bool = Field(default=True)
    sam_circuit_breaker_cooldown_seconds: int = Field(default=900, ge=60, le=86400)
    sam_circuit_breaker_max_seconds: int = Field(default=3600, ge=60, le=86400)
    
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model_pro: str = Field(default="gemini-1.5-pro")
    gemini_model_flash: str = Field(default="gemini-1.5-flash")
    mock_ai: bool = Field(default=False)
    mock_sam_gov: bool = Field(default=False)
    mock_sam_gov_variant: str = Field(default="v1")
    sam_mock_attachments_dir: Optional[str] = Field(default=None)

    # -------------------------------------------------------------------------
    # File Storage
    # -------------------------------------------------------------------------
    upload_dir: str = Field(default="/app/uploads")
    max_upload_size_mb: int = Field(default=50)

    # -------------------------------------------------------------------------
    # JWT Auth Settings
    # -------------------------------------------------------------------------
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    sentry_dsn: Optional[str] = Field(default=None)
    sentry_environment: str = Field(default="development")
    sentry_traces_sample_rate: float = Field(default=0.1)
    log_level: str = Field(default="INFO")
    enable_metrics: bool = Field(default=True)
    webhook_delivery_enabled: bool = Field(default=False)

    @field_validator("sam_gov_api_key", "gemini_api_key", mode="before")
    @classmethod
    def validate_api_keys(cls, v: Optional[str]) -> Optional[str]:
        """Ensure API keys are not placeholder values."""
        if v and v.startswith("your_"):
            return None
        return v

    @property
    def sync_database_url(self) -> str:
        """Convert async URL to sync for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Use dependency injection in FastAPI routes.
    """
    return Settings()


# Convenience export
settings = get_settings()
