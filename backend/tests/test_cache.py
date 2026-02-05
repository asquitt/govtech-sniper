"""
RFP Sniper - Cache Service Tests
================================
Unit tests for in-memory cache behavior.
"""

import pytest

from app.services.cache_service import MemoryCache


class TestMemoryCache:
    @pytest.mark.asyncio
    async def test_memory_cache_ttl(self):
        cache = MemoryCache()
        await cache.set("key", {"value": 123}, ttl_seconds=1)
        assert await cache.get("key") == {"value": 123}

        await cache.set("key2", "temp", ttl_seconds=0)
        assert await cache.get("key2") == "temp"

    @pytest.mark.asyncio
    async def test_memory_cache_clear_and_prefix(self):
        cache = MemoryCache()
        await cache.set("rfps:list:1:all", [1], ttl_seconds=10)
        await cache.set("rfps:list:1:status", [2], ttl_seconds=10)
        await cache.set("rfps:detail:1", {"id": 1}, ttl_seconds=10)

        await cache.clear_prefix("rfps:list:1:")
        assert await cache.get("rfps:list:1:all") is None
        assert await cache.get("rfps:list:1:status") is None
        assert await cache.get("rfps:detail:1") == {"id": 1}

        await cache.clear()
        assert await cache.get("rfps:detail:1") is None
