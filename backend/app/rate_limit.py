"""Simple in-memory per-client-IP rate limiter.

Hand-rolled rather than a dependency: CLAUDE.md rule 13 locks dependencies,
and this project runs as a single process (Railway/HF Spaces free tier), so
an in-memory fixed window is sufficient without adding slowapi or similar.

Both deployment targets sit behind a reverse proxy, so the client key
prefers X-Forwarded-For over the raw socket peer (see _client_key) to keep
"per-IP" meaningful rather than collapsing every request into one shared
bucket keyed on the proxy's own address.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        sweep_interval: int = 1000,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.sweep_interval = sweep_interval
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._calls_since_sweep = 0

    def _client_key(self, request: Request) -> str:
        # Both stated deployment targets (Railway, HF Spaces free tier) sit
        # behind a reverse proxy, so request.client.host alone would be the
        # proxy's own IP for every request, collapsing "per-IP" into one
        # shared global bucket. Prefer the leftmost X-Forwarded-For entry
        # (the original client, per the header's append-per-hop convention)
        # when present, falling back to the direct socket peer otherwise.
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _sweep_idle_keys(self, now: float) -> None:
        # Caller must hold self._lock. Evicts keys whose deque is empty or
        # whose most recent hit has already aged out of the window, so the
        # dict doesn't grow unboundedly for a long-running single process.
        idle_keys = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] > self.window_seconds
        ]
        for key in idle_keys:
            del self._hits[key]

    def check(self, request: Request) -> None:
        key = self._client_key(request)
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

            self._calls_since_sweep += 1
            if self._calls_since_sweep >= self.sweep_interval:
                self._sweep_idle_keys(now)
                self._calls_since_sweep = 0

    def __call__(self, request: Request) -> None:
        self.check(request)
