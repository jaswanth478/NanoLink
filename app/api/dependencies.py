from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.redis_client import get_redis_client
from app.services.cache import UrlCache
from app.services.idempotency import IdempotencyStore
from app.services.click_logger import ClickLogger
from app.services.shortener_service import ShortenerService


async def get_db_session() -> AsyncSession:
    async with get_session() as session:
        yield session


async def get_shortener_service() -> ShortenerService:
    async with get_session() as session:
        redis = get_redis_client()
        cache = UrlCache(redis)
        idempotency = IdempotencyStore(redis)
        click_logger = ClickLogger(redis)
        service = ShortenerService(session, cache, click_logger, idempotency)
        yield service
