from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    telegram_webhook_secret: str = ""
    bot_webhook_url: str = ""
    database_url: str = "sqlite:///./marketpilot.db"
    webapp_url: str = "http://localhost:8080"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
