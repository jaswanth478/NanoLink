from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.api.dependencies import get_shortener_service


class _DummyDB:
    async def execute(self, *_args, **_kwargs):
        class _Result:
            def scalar_one_or_none(self):
                return None

        return _Result()


class _DummyCacheClient:
    async def ping(self):
        return "PONG"


class _DummyCache:
    def __init__(self):
        self.client = _DummyCacheClient()


class DummyShortenerService:
    def __init__(self):
        self.db = _DummyDB()
        self.cache = _DummyCache()
        self._store: dict[str, str] = {}
        self.logged_clicks: list[str] = []

    async def create_short_url(self, *, original_url: str, client_ip: str, custom_alias: str | None, idempotency_key: str | None):
        code = custom_alias or f"code{len(self._store) + 1}"
        self._store[code] = original_url
        return {"short_code": code, "original_url": original_url}

    async def resolve_short_code(self, short_code: str):
        if short_code not in self._store:
            raise LookupError("missing")
        return {"short_code": short_code, "original_url": self._store[short_code]}

    async def log_click(self, short_code: str, *, ip: str, referrer: str | None, user_agent: str | None):
        self.logged_clicks.append(short_code)


@pytest.fixture()
def client_and_service():
    app = FastAPI()
    app.include_router(routes.router)
    service = DummyShortenerService()

    async def override_service():
        yield service

    app.dependency_overrides[get_shortener_service] = override_service

    with TestClient(app) as client:
        yield client, service


def test_health_endpoints(client_and_service):
    client, _ = client_and_service
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_shorten_and_redirect_flow(client_and_service):
    client, service = client_and_service
    payload = {"original_url": "https://google.com/"}
    resp = client.post("/shorten", json=payload, headers={"Idempotency-Key": "abc"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["original_url"] == payload["original_url"]

    redirect = client.get(f"/{data['short_code']}", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == payload["original_url"]

    assert data["short_code"] in service.logged_clicks



