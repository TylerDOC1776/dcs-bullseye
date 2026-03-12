"""
API key authentication dependency for orchestrator routes.

Reads X-API-Key header and compares against config.api_key.
Empty api_key = auth disabled (dev mode). Missing/wrong key → 403.

After 5 failed auth attempts from the same IP within 5 minutes the IP
is locked out for 5 minutes (returns 429).
"""

from __future__ import annotations

import hmac
import logging
import time
from threading import Lock

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_MAX_FAILS = 5
_FAIL_WINDOW = 300  # seconds
_LOCKOUT_DURATION = 300  # seconds


class _FailedAuthTracker:
    def __init__(
        self,
        max_fails: int = _MAX_FAILS,
        window: int = _FAIL_WINDOW,
        lockout: int = _LOCKOUT_DURATION,
    ) -> None:
        self._records: dict[str, tuple[int, float, float]] = {}
        self._max_fails = max_fails
        self._window = window
        self._lockout = lockout
        self._lock = Lock()

    def is_locked(self, ip: str) -> bool:
        with self._lock:
            rec = self._records.get(ip)
            if rec is None:
                return False
            _, _, locked_until = rec
            if locked_until and time.time() < locked_until:
                return True
            del self._records[ip]
            return False

    def record_failure(self, ip: str) -> None:
        now = time.time()
        with self._lock:
            rec = self._records.get(ip)
            if rec is None:
                self._records[ip] = (1, now, 0.0)
                return
            count, window_start, locked_until = rec
            if now - window_start > self._window:
                self._records[ip] = (1, now, 0.0)
                return
            count += 1
            if count >= self._max_fails:
                locked_until = now + self._lockout
                logger.warning(
                    "auth: locking out %s for %ds after %d failures",
                    ip,
                    self._lockout,
                    count,
                )
            self._records[ip] = (count, window_start, locked_until)

    def record_success(self, ip: str) -> None:
        with self._lock:
            self._records.pop(ip, None)


_failed_auth = _FailedAuthTracker()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def require_api_key(
    request: Request,
    api_key: str | None = Depends(_api_key_header),
) -> None:
    config = request.app.state.config
    if not config.api_key:
        # Dev mode — auth disabled (warned at startup)
        return

    ip = _client_ip(request)

    if _failed_auth.is_locked(ip):
        raise HTTPException(
            status_code=429, detail="Too many failed auth attempts — try again later"
        )

    if not api_key or not hmac.compare_digest(api_key, config.api_key):
        _failed_auth.record_failure(ip)
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    _failed_auth.record_success(ip)
