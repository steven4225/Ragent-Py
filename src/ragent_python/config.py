from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="PYTHON_ENV")
    log_level: str = Field(default="info", alias="PYTHON_LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="PYTHON_HOST")
    port: int = Field(default=8000, alias="PYTHON_PORT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
