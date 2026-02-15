"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    postgres_db: str = "corridor"
    postgres_user: str = "corridor_admin"
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    
    # Application
    debug: bool = False
    log_level: str = "INFO"
    
    # Week Configuration
    week_deadline_day: str = "sunday"
    week_deadline_hour: int = 12
    week_deadline_minute: int = 0
    
    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def async_database_url(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Global settings instance
settings = Settings()
