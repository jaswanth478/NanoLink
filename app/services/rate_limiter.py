from __future__ import annotations

import time
from typing import Tuple

import redis.asyncio as redis

LUA_TOKEN_BUCKET = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local bucket = redis.call('HMGET', key, 'tokens', 'timestamp')
local tokens = tonumber(bucket[1])
local timestamp = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  timestamp = now
end

local delta = math.max(0, now - timestamp)
tokens = math.min(capacity, tokens + delta * refill_rate)

local allowed = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'timestamp', now)
redis.call('EXPIRE', key, ttl)

return {allowed, tokens}
"""


class RedisRateLimiter:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client
        self.script = self.client.register_script(LUA_TOKEN_BUCKET)

    async def allow(self, key: str, capacity: int, window_seconds: int, cost: int = 1) -> Tuple[bool, float]:
        refill_rate = capacity / window_seconds
        ttl = window_seconds * 2
        now = time.time()
        allowed, tokens = await self.script(keys=[key], args=[capacity, refill_rate, cost, now, ttl])
        return bool(allowed), float(tokens)
