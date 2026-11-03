"""Per-IP rate limit for the endpoints that call Gemini, for public (demo) deployments.

Off unless RATE_LIMIT_ENABLED=true (the Dockerfile turns it on). Each client IP gets at most
RATE_LIMIT_PER_MINUTE (default 10) and RATE_LIMIT_PER_DAY (default 100) requests across the
limited endpoints together; over the limit it gets a 429 with a plain message the frontend shows.
Counts live in memory (one container, reset on restart). IPs are never logged or stored.

Behind a proxy (Hugging Face Spaces) every request arrives from the proxy, so the client IP is
read from X-Forwarded-For -- but only when RATE_LIMIT_TRUST_PROXY=true, since the header can be
set by anyone when there is no proxy in front.
"""
from __future__ import annotations

import os
import re
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# (method, path pattern) of every endpoint that can make a Gemini request.
LIMITED_ENDPOINTS = (
    ("POST", re.compile(r"^/api/ask$")),
    ("POST", re.compile(r"^/api/transcribe$")),
    ("POST", re.compile(r"^/api/scam-check$")),
    ("POST", re.compile(r"^/api/documents/extract-facts$")),
    ("POST", re.compile(r"^/api/documents/[^/]+/summarize$")),
)
MINUTE_MESSAGE = "Too many requests from your connection. Please wait a minute and try again."
DAY_MESSAGE = "You've reached today's limit for this demo. Please try again tomorrow."


def env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


class RateLimiter:
    def __init__(self, enabled: bool, per_minute: int, per_day: int, trust_proxy: bool) -> None:
        self.enabled = enabled
        self.per_minute = per_minute
        self.per_day = per_day
        self.trust_proxy = trust_proxy
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "RateLimiter":
        return cls(
            enabled=env_flag("RATE_LIMIT_ENABLED"),
            per_minute=env_int("RATE_LIMIT_PER_MINUTE", 10),
            per_day=env_int("RATE_LIMIT_PER_DAY", 100),
            trust_proxy=env_flag("RATE_LIMIT_TRUST_PROXY"),
        )

    def client_ip(self, request: Request) -> str:
        if self.trust_proxy:
            forwarded = request.headers.get("x-forwarded-for", "")
            if forwarded.strip():
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, ip: str, now: float | None = None) -> str | None:
        """None if the request may go ahead (and is counted); otherwise the message to return."""
        now = time.time() if now is None else now
        with self._lock:
            hits = self._hits[ip]
            while hits and now - hits[0] >= 86400:
                hits.popleft()
            if len(hits) >= self.per_day:
                return DAY_MESSAGE
            if sum(1 for t in hits if now - t < 60) >= self.per_minute:
                return MINUTE_MESSAGE
            hits.append(now)
            return None


LIMITER = RateLimiter.from_env()


def is_limited(method: str, path: str) -> bool:
    return any(method == m and pattern.match(path) for m, pattern in LIMITED_ENDPOINTS)


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def rate_limit_gemini_endpoints(request: Request, call_next):
        limiter = LIMITER
        if limiter.enabled and is_limited(request.method, request.url.path):
            message = limiter.check(limiter.client_ip(request))
            if message:
                retry_after = "60" if message == MINUTE_MESSAGE else "3600"
                return JSONResponse(status_code=429, content={"detail": message}, headers={"Retry-After": retry_after})
        return await call_next(request)
