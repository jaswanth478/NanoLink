from __future__ import annotations

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.rate_limiter import RedisRateLimiter
from config.settings import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RedisRateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        
        if request.url.path in ["/health/live", "/health/ready"]:
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        try:
            ip_allowed, _ = await self.limiter.allow(
                key=f"rate:ip:{client_ip}",
                capacity=settings.rate_limit_ip,
                window_seconds=settings.token_bucket_window_seconds,
            )
            if not ip_allowed:
                return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Too many requests"})

            global_allowed, _ = await self.limiter.allow(
                key="rate:global",
                capacity=settings.rate_limit_global,
                window_seconds=settings.token_bucket_window_seconds,
            )
            if not global_allowed:
                return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Service busy"})
        except Exception:
            # If rate limiting fails (Redis down), allow request but log error
            # Health checks should still work even if Redis is unavailable
            pass

        return await call_next(request)
