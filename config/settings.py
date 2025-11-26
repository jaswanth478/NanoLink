from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "short-url-service"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    database_url: str
    redis_url: str
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: str | None = None

    rate_limit_ip: int = 50
    rate_limit_global: int = 1000
    token_bucket_window_seconds: int = 60
    cache_ttl_seconds: int = 3600
    idempotency_ttl_seconds: int = 3600
    click_stream_key: str = "shortener:clicks"

    allowed_origins: List[AnyHttpUrl] | str = []
    secure_cookies: bool = False

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
