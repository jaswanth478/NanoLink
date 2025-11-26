from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

from app.api.schemas import HealthResponse, ShortenRequest, ShortenResponse
from app.api.dependencies import get_shortener_service
from app.services.shortener_service import ShortenerService

router = APIRouter()


@router.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(service: ShortenerService = Depends(get_shortener_service)) -> HealthResponse:
    from config.settings import get_settings
    
    settings = get_settings()
    db_url = settings.database_url
    
    # Check if database URL is in correct format
    if not db_url.startswith("postgresql+asyncpg://"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database URL must start with 'postgresql+asyncpg://', got: {db_url[:30]}..."
        )
    
    # Check if SSL mode is set (Railway requires it)
    if "sslmode" not in db_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database URL missing '?sslmode=require' - Railway Postgres requires SSL"
        )
    
    try:
        await service.db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )
    
    try:
        await service.cache.client.ping()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {str(e)}"
        )
    
    return HealthResponse(status="ready")


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    request: Request,
    service: ShortenerService = Depends(get_shortener_service),
) -> ShortenResponse:
    idempotency_key = request.headers.get("Idempotency-Key")
    try:
        result = await service.create_short_url(
            original_url=str(payload.original_url),
            client_ip=request.client.host if request.client else "unknown",
            custom_alias=payload.custom_alias,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return ShortenResponse(**result)


@router.get("/{short_code}")
async def redirect_short_code(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    service: ShortenerService = Depends(get_shortener_service),
):
    try:
        result = await service.resolve_short_code(short_code)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found")

    background_tasks.add_task(
        service.log_click,
        short_code=short_code,
        ip=request.client.host if request.client else "unknown",
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
    )

    return RedirectResponse(result["original_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT)
