
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    webapp_url: str = ""
    database_url: str = "sqlite:///./marketpilot.db"
    webhook_secret: str = ""
    allow_dev_user: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False
    )


settings = Settings()
