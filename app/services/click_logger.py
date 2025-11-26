from __future__ import annotations

from typing import Any

import redis.asyncio as redis

from config.settings import get_settings

settings = get_settings()


class ClickLogger:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client
        self.stream_key = settings.click_stream_key

    async def log_click(self, *, short_code: str, ip: str, referrer: str | None, user_agent: str | None) -> None:
        await self.client.xadd(
            self.stream_key,
            {
                "short_code": short_code,
                "ip": ip,
                "referrer": referrer or "",
                "user_agent": user_agent or "",
            },
            maxlen=10000,
            approximate=True,
        )
