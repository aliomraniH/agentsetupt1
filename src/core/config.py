"""
Configuration management for the application
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import os


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
    alpha_vantage_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True  # Changed to True for Replit secrets compatibility

    def __init__(self, **kwargs):
        """Custom init to handle Replit environment variables"""
        super().__init__(**kwargs)

        # Fallback: Manually check environment variables if pydantic didn't load them
        # This handles cases where Replit secrets aren't picked up by pydantic

        if not self.anthropic_api_key:
            # Try exact match first
            env_key = os.environ.get("ANTHROPIC_API_KEY")
            if env_key and env_key.strip():  # Check it's not empty/whitespace
                self.anthropic_api_key = env_key.strip()
                print(f"✅ Loaded ANTHROPIC_API_KEY from environment (fallback): {env_key[:20]}...")

        if not self.alpha_vantage_api_key:
            env_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
            if env_key and env_key.strip():
                self.alpha_vantage_api_key = env_key.strip()

        if not self.perplexity_api_key:
            env_key = os.environ.get("PERPLEXITY_API_KEY")
            if env_key and env_key.strip():
                self.perplexity_api_key = env_key.strip()



@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
