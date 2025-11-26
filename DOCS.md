# Project Documentation

This document describes every top-level folder and notable file in the Short URL Service repository, explaining its responsibilities and how it fits into the system.

## Root Files

- `README.md` – high-level overview, feature list, and quick start instructions, plus a link to deployment manifests and how to run tests.
- `pyproject.toml` – project metadata and dependency declarations for Poetry/pip (FastAPI, SQLAlchemy, Redis, etc.).
- `requirements.txt` – flattened dependency list for production deployments (used by Railway, containers, etc.).
- `.gitignore` – excludes virtual environments, secrets, cache/build artifacts, editor files, and OS clutter.
- `.env` *(ignored)* – local runtime configuration; copy from `config/.env.example`.
- `.venv/` *(ignored)* – developer’s local virtual environment; not part of the deployable artifact.
- `alembic.ini` – Alembic configuration pointing migrations to `app/db/migrations`.

## `config/`

- `settings.py` – Pydantic-based configuration loader that reads environment variables, applies defaults, and provides `get_settings()` for dependency injection.
- `.env.example` *(ignored in repo tree output but present)* – template env file listing required variables (DB URL, Redis URL, rate limits, etc.).

## `app/`

### `app/main.py`
FastAPI application bootstrap: configures logging, CORS, Redis client, rate-limiter middleware, security headers, exception handler, and lifecycle events, then mounts the API router.

### `app/api/`
- `routes.py` – defines `/health/live`, `/health/ready`, `POST /shorten`, and redirect `GET /{short_code}` endpoints. Handles idempotency header, error mapping, and asynchronous click logging.
- `schemas.py` – Pydantic request/response models (`ShortenRequest`, `ShortenResponse`, `HealthResponse`).
- `dependencies.py` – FastAPI dependency providers supplying DB sessions and fully-wired `ShortenerService` instances.

### `app/middleware/`
- `logging.py` – structured JSON request logging middleware (adds request IDs, latency).
- `rate_limit.py` – enforces IP-based and global token buckets via Redis scripts, returning HTTP 429 when limits are exceeded.
- `security_headers.py` – injects HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy headers on every response.

### `app/services/`
- `redis_client.py` – lazy singleton that instantiates the asyncio Redis client from configuration.
- `rate_limiter.py` – Redis-backed token bucket implementation using a Lua script for atomic refill/decrement across replicas.
- `cache.py` – typed Redis cache wrapper for short-code ↔ URL payloads with TTL management.
- `idempotency.py` – stores POST `/shorten` responses keyed by `Idempotency-Key` with expiration to guarantee idempotent behavior.
- `short_code.py` – secure random short-code generator using alphanumeric alphabet.
- `click_logger.py` – pushes click metadata onto a Redis Stream for asynchronous processing.
- `shortener_service.py` – main business logic orchestrating DB inserts/selects, cache reads/writes, idempotency checks, and click logging. Handles collision retries, expiry enforcement, and custom aliases.

### `app/db/`
- `models.py` – SQLAlchemy ORM definitions for `UrlMapping` and `ClickEvent` tables with indexes/constraints.
- `session.py` – async engine and session factory (`get_session`) configured from settings.
- `migrations/`
  - `env.py` – Alembic environment script binding metadata and configuring online/offline runs.
  - `versions/20231126_initial.py` – initial migration creating `url_mappings` and `click_events` tables plus indexes.

### `app/utils/`
- `logging.py` – configures structlog + stdlib logging to emit JSON logs with timestamps, levels, and exception details.

## `workers/`

- `click_consumer.py` – background worker that consumes Redis Stream entries (`shortener:clicks`), persists them as `ClickEvent` records, and increments aggregate click counts. Creates consumer groups and handles acknowledgments.

## `infra/`

- `Procfile` – declares the web (uvicorn) and worker (Redis Stream consumer) processes for Railway/Heroku-style platforms.
- `railway.toml` – Railway deployment manifest: replica counts, autoscaling thresholds, health check path, command definitions, and shared env file reference for web + worker services.
- `nginx/lb.conf` – sample Nginx configuration for load-balancing multiple FastAPI instances, forwarding headers, and routing health checks.

## `tests/`

- `unit/test_shortener_service.py` – pytest suite validating idempotency behavior, cache-first resolution, and retry logic under unique constraint collisions using AsyncMock dependencies.
- `integration/test_api.py` – FastAPI TestClient-based integration tests with dependency overrides verifying health endpoints, shorten flow, redirect behavior, and background click logging hooks.

## Supporting Assets

- `workers/` (covered above) ensures click logging is decoupled.
- `tests/` directories serve as structure for future scenarios (expand `integration/` or `unit/` as needed).

This layout keeps concerns separated: API, middleware, services, data access, background processing, infrastructure configs, and automated tests each live in dedicated folders for easier maintenance and scaling.

