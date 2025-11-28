from __future__ import annotations

import asyncio

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.rate_limiter import RedisRateLimiter
from app.services.redis_client import get_redis_client
from app.utils.logging import configure_logging
from config.settings import get_settings

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

allowed_origins = settings.allowed_origins or ["https://nanourl.up.railway.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = get_redis_client()
rate_limiter = RedisRateLimiter(redis_client)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

app.include_router(routes.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})


@app.on_event("startup")
async def startup_event():
    await redis_client.ping()


@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()
