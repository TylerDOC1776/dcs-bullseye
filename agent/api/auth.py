"""
API key authentication dependency for agent routes.

Reads X-API-Key header and compares against config.api_key.
Empty api_key = auth disabled (dev mode). Missing/wrong key → 403.

When api_key is set, also validates HMAC replay-protection headers
(X-Timestamp, X-Nonce, X-Signature) sent by the orchestrator:
  - X-Timestamp must be within ±60s of server time
  - X-Nonce must not have been seen before within the expiry window
  - X-Signature = HMAC-SHA256(api_key, "METHOD\npath\ntimestamp\nnonce")

After 5 failed auth attempts from the same IP within 5 minutes the IP
is locked out for 5 minutes (returns 429).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from threading import Lock

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_TIMESTAMP_SKEW = 60        # seconds allowed either side of now
_NONCE_TTL = 120            # seconds to remember nonces (2× skew window)
_MAX_FAILS = 5              # failed attempts before lockout
_FAIL_WINDOW = 300          # seconds to track failures in
_LOCKOUT_DURATION = 300     # lockout length in seconds


# ------------------------------------------------------------------
# Nonce store — prevents request replay within the skew window
# ------------------------------------------------------------------

class NonceStore:
    """Thread-safe in-memory nonce store with TTL eviction."""

    def __init__(self, ttl: int = _NONCE_TTL) -> None:
        self._seen: dict[str, float] = {}  # nonce → expiry epoch
        self._ttl = ttl
        self._lock = Lock()

    def check_and_add(self, nonce: str, now: float | None = None) -> bool:
        """Return True and record the nonce if it is fresh. Return False on replay."""
        t = now if now is not None else time.time()
        with self._lock:
            self._evict(t)
            if nonce in self._seen:
                return False
            self._seen[nonce] = t + self._ttl
            return True

    def _evict(self, now: float) -> None:
        expired = [n for n, exp in self._seen.items() if exp <= now]
        for n in expired:
            del self._seen[n]


# ------------------------------------------------------------------
# Failed-auth tracker — IP lockout after repeated failures
# ------------------------------------------------------------------

class _FailedAuthTracker:
    def __init__(
        self,
        max_fails: int = _MAX_FAILS,
        window: int = _FAIL_WINDOW,
        lockout: int = _LOCKOUT_DURATION,
    ) -> None:
        # ip → (fail_count, window_start, locked_until)
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
            # Lockout expired — clear
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
                # Old window expired — start fresh
                self._records[ip] = (1, now, 0.0)
                return
            count += 1
            if count >= self._max_fails:
                locked_until = now + self._lockout
                logger.warning("auth: locking out %s for %ds after %d failures", ip, self._lockout, count)
            self._records[ip] = (count, window_start, locked_until)

    def record_success(self, ip: str) -> None:
        with self._lock:
            self._records.pop(ip, None)


_failed_auth = _FailedAuthTracker()


# ------------------------------------------------------------------
# Auth dependency
# ------------------------------------------------------------------

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
        # Dev mode — auth disabled
        return

    ip = _client_ip(request)

    if _failed_auth.is_locked(ip):
        raise HTTPException(status_code=429, detail="Too many failed auth attempts — try again later")

    # 1. Validate API key
    if not api_key or not hmac.compare_digest(api_key, config.api_key):
        _failed_auth.record_failure(ip)
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    # 2. Validate replay-protection headers (optional — skip gracefully if absent,
    #    so legacy/dev callers without signing still work when the key is correct.
    #    Full enforcement is done when all three headers are present.)
    ts_hdr = request.headers.get("X-Timestamp")
    nonce_hdr = request.headers.get("X-Nonce")
    sig_hdr = request.headers.get("X-Signature")

    if ts_hdr or nonce_hdr or sig_hdr:
        # At least one signing header present — enforce all three
        if not (ts_hdr and nonce_hdr and sig_hdr):
            _failed_auth.record_failure(ip)
            raise HTTPException(status_code=403, detail="Incomplete request signing headers")

        # Validate timestamp skew
        try:
            req_time = int(ts_hdr)
        except ValueError:
            _failed_auth.record_failure(ip)
            raise HTTPException(status_code=403, detail="Invalid X-Timestamp")

        now = time.time()
        if abs(now - req_time) > _TIMESTAMP_SKEW:
            _failed_auth.record_failure(ip)
            raise HTTPException(status_code=403, detail="Request timestamp out of range")

        # Validate HMAC signature
        method = request.method.upper()
        path = request.url.path
        msg = f"{method}\n{path}\n{ts_hdr}\n{nonce_hdr}"
        expected = hmac.new(config.api_key.encode(), msg.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_hdr, expected):
            _failed_auth.record_failure(ip)
            raise HTTPException(status_code=403, detail="Invalid request signature")

        # Validate nonce freshness
        nonce_store: NonceStore = request.app.state.nonce_store
        if not nonce_store.check_and_add(nonce_hdr, now):
            _failed_auth.record_failure(ip)
            raise HTTPException(status_code=403, detail="Replayed request nonce")

    _failed_auth.record_success(ip)
