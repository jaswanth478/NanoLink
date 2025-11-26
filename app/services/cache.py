from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as redis

from config.settings import get_settings

settings = get_settings()


class UrlCache:
    def __init__(self, client: redis.Redis, ttl_seconds: int | None = None) -> None:
        self.client = client
        self.ttl = ttl_seconds or settings.cache_ttl_seconds

    @staticmethod
    def _key(short_code: str) -> str:
        return f"cache:url:{short_code}"

    async def get(self, short_code: str) -> Optional[dict[str, Any]]:
        payload = await self.client.get(self._key(short_code))
        return json.loads(payload) if payload else None

    async def set(self, short_code: str, data: dict[str, Any]) -> None:
        await self.client.setex(self._key(short_code), self.ttl, json.dumps(data))

    async def delete(self, short_code: str) -> None:
        await self.client.delete(self._key(short_code))
