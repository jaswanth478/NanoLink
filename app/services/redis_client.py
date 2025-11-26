from typing import Optional
import redis.asyncio as redis

from config.settings import get_settings

_settings = get_settings()
_redis: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(_settings.redis_url, decode_responses=True)
    return _redis
