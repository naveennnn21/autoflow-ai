"""Regression test: the Redis client used for caching is created with timeouts.

Without an explicit socket timeout a hung/unreachable Redis can block request
handling indefinitely; the cache client must mirror ``app.core.redis_state``.
"""
import pytest

import app.core.cache as cache


@pytest.mark.asyncio
async def test_init_cache_bounds_redis_calls(monkeypatch):
    captured = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        cache, "Redis", type("FakeRedis", (), {"from_url": staticmethod(fake_from_url)})
    )
    try:
        await cache.init_cache()
    finally:
        cache.redis_client = None

    assert captured["socket_connect_timeout"] == 2
    assert captured["socket_timeout"] == 2
