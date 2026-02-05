"""
RFP Sniper - Cache Service
==========================
Redis-backed or in-memory cache with TTL support.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class MemoryCache:
    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    async def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at and time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else 0
        self._store[key] = (expires_at, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear_prefix(self, prefix: str) -> None:
        keys = [key for key in self._store.keys() if key.startswith(prefix)]
        for key in keys:
            self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()


class RedisCache:
    def __init__(self, redis_url: str):
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[Any]:
        value = await self._redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value, default=str)
        await self._redis.set(key, payload, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def clear_prefix(self, prefix: str) -> None:
        async for key in self._redis.scan_iter(match=f"{prefix}*"):
            await self._redis.delete(key)

    async def clear(self) -> None:
        await self._redis.flushdb()


_cache_backend = None


def get_cache_backend():
    global _cache_backend
    if _cache_backend:
        return _cache_backend

    if settings.cache_backend.lower() == "redis":
        _cache_backend = RedisCache(settings.redis_url)
        logger.info("Cache backend initialized", backend="redis")
    else:
        _cache_backend = MemoryCache()
        logger.info("Cache backend initialized", backend="memory")
    return _cache_backend


async def cache_get(key: str) -> Optional[Any]:
    backend = get_cache_backend()
    return await backend.get(key)


async def cache_set(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    backend = get_cache_backend()
    ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
    await backend.set(key, value, ttl)


async def cache_delete(key: str) -> None:
    backend = get_cache_backend()
    await backend.delete(key)


async def cache_clear_prefix(prefix: str) -> None:
    backend = get_cache_backend()
    await backend.clear_prefix(prefix)


async def cache_clear() -> None:
    backend = get_cache_backend()
    await backend.clear()
