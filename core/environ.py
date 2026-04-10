from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    MAIN_BOT_TOKEN: str
    CLIENT_BOT_TOKEN: str
    WEBHOOK_BASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"   # 👈 MUHIM FIX
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()