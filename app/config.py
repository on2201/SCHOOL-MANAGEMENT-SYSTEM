from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SMS_")
    database_url: str = "sqlite:///./school.db"
    secret_key: str = "dev-insecure-change-me"
    algorithm: str = "HS256"
    access_token_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:3000"]

@lru_cache
def get_settings() -> Settings:
    return Settings()
