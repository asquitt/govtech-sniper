"""
Cache Service Unit Tests
=========================
Tests for MemoryCache (no Redis dependency).
"""

import pytest

from app.services.cache_service import MemoryCache


@pytest.fixture
def cache():
    return MemoryCache()


class TestMemoryCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: MemoryCache):
        await cache.set("key1", "value1", ttl_seconds=300)
        assert await cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self, cache: MemoryCache):
        assert await cache.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_delete(self, cache: MemoryCache):
        await cache.set("key1", "value1", ttl_seconds=300)
        await cache.delete("key1")
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache: MemoryCache):
        # Should not raise
        await cache.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_clear(self, cache: MemoryCache):
        await cache.set("a", 1, ttl_seconds=300)
        await cache.set("b", 2, ttl_seconds=300)
        await cache.clear()
        assert await cache.get("a") is None
        assert await cache.get("b") is None

    @pytest.mark.asyncio
    async def test_clear_prefix(self, cache: MemoryCache):
        await cache.set("user:1:name", "Alice", ttl_seconds=300)
        await cache.set("user:1:email", "a@b.com", ttl_seconds=300)
        await cache.set("other:key", "val", ttl_seconds=300)
        await cache.clear_prefix("user:1:")
        assert await cache.get("user:1:name") is None
        assert await cache.get("user:1:email") is None
        assert await cache.get("other:key") == "val"

    @pytest.mark.asyncio
    async def test_expired_key_returns_none(self, cache: MemoryCache):
        # Set TTL to 0 (already expired — expires_at = time.time() + 0 = now)
        # Due to granularity, manually set a past expiry
        import time

        cache._store["expired"] = (time.time() - 1, "stale")
        assert await cache.get("expired") is None

    @pytest.mark.asyncio
    async def test_stores_complex_types(self, cache: MemoryCache):
        data = {"users": [{"id": 1, "name": "Alice"}], "count": 1}
        await cache.set("complex", data, ttl_seconds=300)
        assert await cache.get("complex") == data

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self, cache: MemoryCache):
        await cache.set("key", "v1", ttl_seconds=300)
        await cache.set("key", "v2", ttl_seconds=300)
        assert await cache.get("key") == "v2"
