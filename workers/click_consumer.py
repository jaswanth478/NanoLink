import asyncio
import socket

import redis.asyncio as redis
from sqlalchemy import update

from app.db.session import get_session
from app.db import models
from app.services.redis_client import get_redis_client
from config.settings import get_settings

settings = get_settings()
STREAM = settings.click_stream_key
GROUP = "click_loggers"
CONSUMER_NAME = f"worker-{socket.gethostname()}"


async def ensure_group(client: redis.Redis) -> None:
    try:
        await client.xgroup_create(name=STREAM, groupname=GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:  # BUSYGROUP
        if "BUSYGROUP" not in str(exc):
            raise


async def handle_entry(data: dict[str, str]) -> None:
    async with get_session() as session:
        event = models.ClickEvent(
            short_code=data.get("short_code"),
            client_ip=data.get("ip"),
            referrer=data.get("referrer") or None,
            user_agent=data.get("user_agent") or None,
        )
        session.add(event)
        await session.execute(
            update(models.UrlMapping)
            .where(models.UrlMapping.short_code == event.short_code)
            .values(click_count=models.UrlMapping.click_count + 1)
        )
        await session.commit()


async def consume() -> None:
    client = get_redis_client()
    await ensure_group(client)
    while True:
        results = await client.xreadgroup(
            groupname=GROUP,
            consumername=CONSUMER_NAME,
            streams={STREAM: ">"},
            count=100,
            block=5000,
        )
        if not results:
            continue
        for _, entries in results:
            for entry_id, data in entries:
                await handle_entry(data)
                await client.xack(STREAM, GROUP, entry_id)


if __name__ == "__main__":
    asyncio.run(consume())
