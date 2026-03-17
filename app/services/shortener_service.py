from __future__ import annotations

from typing import Optional
import hashlib

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.services.cache import UrlCache
from app.services.short_code import generate_short_code
from app.services.click_logger import ClickLogger
from app.services.idempotency import IdempotencyStore


class ShortenerService:
    def __init__(
        self,
        db: AsyncSession,
        cache: UrlCache,
        click_logger: ClickLogger,
        idempotency_store: IdempotencyStore,
    ) -> None:
        self.db = db
        self.cache = cache
        self.click_logger = click_logger
        self.idempotency_store = idempotency_store

    async def create_short_url(
        self,
        *,
        original_url: str,
        client_ip: str,
        custom_alias: str | None,
        idempotency_key: str | None,
    ) -> dict:
        if not idempotency_key:
            idempotency_key = hashlib.md5(original_url.encode()).hexdigest()
        
        cached = await self.idempotency_store.get(idempotency_key)
        if cached:
            return cached

        short_code = custom_alias or await self._generate_unique_code()
        while True:
            record = models.UrlMapping(
                short_code=short_code,
                original_url=original_url,
                created_by_ip=client_ip,
                idempotency_key=idempotency_key,
            )
            self.db.add(record)
            try:
                await self.db.commit()
                break
            except IntegrityError:
                await self.db.rollback()
                if custom_alias:
                    raise ValueError("Custom alias already in use")
                short_code = await self._generate_unique_code()

        response = {
            "short_code": short_code,
            "original_url": original_url,
        }

        if idempotency_key:
            await self.idempotency_store.set(idempotency_key, response)

        await self.cache.set(short_code, response)
        return response

    async def resolve_short_code(self, short_code: str) -> dict:
        cached = await self.cache.get(short_code)
        if cached:
            return cached

        query = select(models.UrlMapping).where(models.UrlMapping.short_code == short_code)
        result = await self.db.execute(query)
        record = result.scalar_one_or_none()
        if not record:
            raise LookupError("Short code not found")
        if record.expires_at and record.expires_at < datetime.now(timezone.utc):
            raise LookupError("Short code expired")

        payload = {"short_code": record.short_code, "original_url": record.original_url}
        await self.cache.set(short_code, payload)
        return payload

    async def log_click(self, short_code: str, *, ip: str, referrer: Optional[str], user_agent: Optional[str]) -> None:
        await self.click_logger.log_click(short_code=short_code, ip=ip, referrer=referrer, user_agent=user_agent)

    async def _generate_unique_code(self) -> str:
        while True:
            candidate = generate_short_code()
            exists = await self.db.execute(
                select(models.UrlMapping.short_code).where(models.UrlMapping.short_code == candidate)
            )
            if not exists.scalar_one_or_none():
                return candidate
