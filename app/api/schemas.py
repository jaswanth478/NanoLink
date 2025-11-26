from __future__ import annotations

from pydantic import BaseModel, AnyHttpUrl, Field


class ShortenRequest(BaseModel):
    original_url: AnyHttpUrl
    custom_alias: str | None = Field(default=None, max_length=16)


class ShortenResponse(BaseModel):
    short_code: str
    original_url: AnyHttpUrl


class HealthResponse(BaseModel):
    status: str
