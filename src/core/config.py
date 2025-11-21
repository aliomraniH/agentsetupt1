"""
Configuration management for the application
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Back End Health Agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # API
    api_prefix: str = "/api/v1"

    # Authentication (optional for now)
    api_key: Optional[str] = None

    # Health Check defaults
    health_check_timeout: int = 30  # seconds
    health_check_interval: int = 60  # seconds

    # External services (for future use)
    anthropic_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
