"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Green API Configuration
    green_api_instance_id: str = ""
    green_api_token: str = ""

    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./whatsapp_monitor.db"

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
    port: int = 8000  # Port for FastAPI webhook server
    summary_keywords: str = "sikum,סיכום,summary,summarize"  # Comma-separated keywords that trigger summary


# Global settings instance
settings = Settings()
