from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    google_cloud_project: str
    vertex_ai_location: str = "us-central1"
    gemini_model: str = "gemini-3.1-pro-preview"
    redis_url: str = "redis://localhost:6379"
    database_url: str
    phoenix_api_key: str
    phoenix_collector_endpoint: str
    jwt_secret: str
    environment: str = "development"
    port: int = 8000
    confidence_threshold: float = 0.85
    signal_ttl_seconds: int = 300
    max_institutions: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
