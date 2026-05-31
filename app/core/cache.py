from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


class CacheClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._redis: Redis | None = None
        self._fallback: dict[str, tuple[float, str]] = {}

    async def connect(self) -> None:
        self._redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
        try:
            await self._redis.ping()  # type: ignore[misc]
        except RedisError:
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()

    async def get_json(self, key: str) -> Any | None:
        if self._redis:
            try:
                value = await self._redis.get(key)
                return json.loads(value) if value else None
            except RedisError:
                pass
        entry = self._fallback.get(key)
        if not entry:
            return None
        expiry, value = entry
        if time.time() > expiry:
            self._fallback.pop(key, None)
            return None
        return json.loads(value)

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        serialized = json.dumps(value, default=str)
        if self._redis:
            try:
                await self._redis.set(key, serialized, ex=ttl_seconds)
                return
            except RedisError:
                pass
        self._fallback[key] = (time.time() + ttl_seconds, serialized)

    async def invalidate_prefix(self, prefix: str) -> None:
        if self._redis:
            try:
                async for key in self._redis.scan_iter(f"{prefix}*"):
                    await self._redis.delete(key)
            except RedisError:
                pass
        for key in list(self._fallback.keys()):
            if key.startswith(prefix):
                self._fallback.pop(key, None)

    async def cached(
        self,
        key: str,
        producer: Callable[[], Any],
        ttl_seconds: int = 300,
    ) -> Any:
        cached = await self.get_json(key)
        if cached is not None:
            return cached
        value = await producer()
        await self.set_json(key, value, ttl_seconds=ttl_seconds)
        return value


def stable_filters_hash(filters: dict[str, Any]) -> str:
    canonical = json.dumps(filters, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


cache_client = CacheClient()
