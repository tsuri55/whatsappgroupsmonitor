"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # WhatsApp API Configuration
    whatsapp_api_url: str = "http://localhost:3000"
    whatsapp_api_key: str = "your_api_key_here"

    # Database Configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/whatsapp_monitor"

    @property
    def database_sync_url(self) -> str:
        """Convert async database URL to sync version for migrations."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")

    # Google Gemini Configuration
    google_api_key: str
    gemini_llm_model: str = "models/gemini-flash-latest"

    # Notification Configuration
    summary_recipient_phone: str = "+972542607800"
    summary_schedule_hour: int = 20
    summary_schedule_timezone: str = "Asia/Jerusalem"

    # Application Configuration
    log_level: str = "INFO"
    minimum_messages_for_summary: int = 15
    max_messages_per_summary: int = 1000

    # Retry Configuration
    max_retry_attempts: int = 6
    retry_min_wait: int = 1
    retry_max_wait: int = 30


# Global settings instance
settings = Settings()
