from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from config.settings import get_settings

settings = get_settings()


class IdempotencyStore:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client
        self.ttl = settings.idempotency_ttl_seconds

    @staticmethod
    def _key(idempotency_key: str) -> str:
        return f"idempotency:{idempotency_key}"

    async def get(self, idempotency_key: str) -> dict[str, Any] | None:
        payload = await self.client.get(self._key(idempotency_key))
        return json.loads(payload) if payload else None

    async def set(self, idempotency_key: str, payload: dict[str, Any]) -> None:
        await self.client.setex(self._key(idempotency_key), self.ttl, json.dumps(payload))
