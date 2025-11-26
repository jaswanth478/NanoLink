# Short URL Service

Production-grade FastAPI URL shortener with PostgreSQL, Redis caching/rate limiting, and background click logging.

## Features
- IP + global Redis-based rate limiting
- Redis cache for short-code resolution with Postgres fallback
- Idempotent short code generation
- Health checks for load balancers
- Structured JSON logging
- Redis Stream consumer worker for click analytics
- Ready for multi-replica deployments on Railway/Fly.io

## Getting Started
1. Copy `config/.env.example` to `.env` and fill secrets.
2. Create virtual environment and install dependencies:
   ```bash
   uv sync
   ```
3. Run database migrations with Alembic.
4. Start web app: `uvicorn app.main:app --reload`.
5. Start worker: `python workers/click_consumer.py`.

See `infra/` for deployment manifests.

## Testing
Run both unit and integration suites with:

```bash
pytest
```

Set `PYTHONPATH` to project root (or install package in editable mode) before running tests so modules resolve correctly.
