from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.cache import cache_client
from app.core.config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._fallback_counts: dict[str, list[float]] = defaultdict(list)

    async def check(self, request: Request) -> None:
        identifier = request.client.host if request.client else "unknown"
        window = self.settings.rate_limit_window_seconds
        max_requests = self.settings.rate_limit_requests
        now = int(time.time())
        bucket = now // window
        key = f"ratelimit:{identifier}:{bucket}"

        if cache_client._redis:
            try:
                count = await cache_client._redis.incr(key)  # type: ignore[union-attr]
                if count == 1:
                    await cache_client._redis.expire(key, window)  # type: ignore[union-attr]
                if count > max_requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                    )
                return
            except RedisError:
                pass

        timestamps = self._fallback_counts[identifier]
        cutoff = time.time() - window
        timestamps[:] = [ts for ts in timestamps if ts >= cutoff]
        timestamps.append(time.time())
        if len(timestamps) > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
            )


rate_limiter = RateLimiter()
