from __future__ import annotations

from collections import deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


def _client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class InMemoryRateLimiter:
    """Per-process sliding-window rate limiter for auth endpoints.

    Limits are applied per worker — deploying with N uvicorn workers effectively
    multiplies the limit by N. Switch to Redis (e.g. slowapi or fastapi-limiter)
    before horizontally scaling.
    """

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    def enforce(self, request: Request, bucket: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        key = (bucket, _client_identifier(request))
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._hits.get(key)
            if timestamps is not None:
                while timestamps and timestamps[0] <= cutoff:
                    timestamps.popleft()
                if not timestamps:
                    # Evict fully-expired keys so one-off IPs don't leak a deque forever.
                    del self._hits[key]
                    timestamps = None

            if timestamps and len(timestamps) >= limit:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many authentication attempts. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            if timestamps is None:
                timestamps = self._hits[key] = deque()
            timestamps.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# Process-wide singleton. Import this instead of instantiating new limiters.
rate_limiter = InMemoryRateLimiter()
