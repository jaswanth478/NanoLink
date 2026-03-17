from unittest.mock import AsyncMock, Mock
import hashlib

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.shortener_service import ShortenerService


@pytest.mark.anyio
async def test_create_short_url_returns_cached_idempotent_result():
    db = AsyncMock()
    db.add = Mock()
    cache = AsyncMock()
    click_logger = AsyncMock()
    idempotency_store = AsyncMock()

    cached_response = {"short_code": "cached12", "original_url": "https://cached.example"}
    idempotency_store.get.return_value = cached_response

    service = ShortenerService(db, cache, click_logger, idempotency_store)

    result = await service.create_short_url(
        original_url="https://unused.example",
        client_ip="1.1.1.1",
        custom_alias=None,
        idempotency_key="idem-123",
    )

    assert result == cached_response
    idempotency_store.get.assert_awaited_once_with("idem-123")
    db.add.assert_not_called()
    db.commit.assert_not_called()
    cache.set.assert_not_called()


@pytest.mark.anyio
async def test_resolve_short_code_hits_cache_before_db():
    db = AsyncMock()
    db.add = Mock()
    cache = AsyncMock()
    click_logger = AsyncMock()
    idempotency_store = AsyncMock()

    cached_response = {"short_code": "abc123", "original_url": "https://cached.example"}
    cache.get.return_value = cached_response

    service = ShortenerService(db, cache, click_logger, idempotency_store)

    result = await service.resolve_short_code("abc123")

    assert result == cached_response
    cache.get.assert_awaited_once_with("abc123")
    db.execute.assert_not_called()


@pytest.mark.anyio
async def test_create_short_url_retries_on_integrity_error():
    db = AsyncMock()
    db.add = Mock()
    cache = AsyncMock()
    click_logger = AsyncMock()
    idempotency_store = AsyncMock()
    idempotency_store.get.return_value = None

    service = ShortenerService(db, cache, click_logger, idempotency_store)
    service._generate_unique_code = AsyncMock(side_effect=["first", "second"])  # noqa: SLF001

    db.commit.side_effect = [IntegrityError("stmt", {}, Exception("boom")), None]

    result = await service.create_short_url(
        original_url="https://retry.example",
        client_ip="2.2.2.2",
        custom_alias=None,
        idempotency_key=None,
    )

    assert result["short_code"] == "second"
    assert result["original_url"] == "https://retry.example"
    assert db.commit.await_count == 2
    assert db.rollback.await_count == 1
    cache.set.assert_awaited_once_with("second", result)


@pytest.mark.anyio
async def test_create_short_url_same_url_returns_same_code():
    """Test that the same URL always produces the same short code (true idempotency)"""
    db = AsyncMock()
    db.add = Mock()
    cache = AsyncMock()
    click_logger = AsyncMock()
    idempotency_store = AsyncMock()

    url = "https://google.com"
    expected_idem_key = hashlib.md5(url.encode()).hexdigest()

    # First call returns None (cache miss), second call returns cached result
    idempotency_store.get.side_effect = [None, {"short_code": "abc123", "original_url": url}]
    service = ShortenerService(db, cache, click_logger, idempotency_store)
    service._generate_unique_code = AsyncMock(return_value="abc123")

    # First request
    result1 = await service.create_short_url(
        original_url=url,
        client_ip="1.1.1.1",
        custom_alias=None,
        idempotency_key=None,
    )

    # Second request with same URL (no explicit idempotency_key)
    result2 = await service.create_short_url(
        original_url=url,
        client_ip="2.2.2.2",
        custom_alias=None,
        idempotency_key=None,
    )

    # Both should return same short code
    assert result1["short_code"] == "abc123"
    assert result2["short_code"] == "abc123"
    
    # Idempotency key should be based on URL hash
    assert idempotency_store.get.call_count == 2
    idempotency_store.get.assert_any_call(expected_idem_key)
