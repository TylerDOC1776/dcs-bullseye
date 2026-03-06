# DCS Bot Security Review

This document tracks security items and their implementation status.

---

## Resolved

### 1. ~~Installer Delivery and Bootstrap Trust~~ ✅
`scripts/install-agent.ps1` now requires `$OrchestratorUrl` (HTTPS enforced at runtime — throws if HTTP).
Optional `$AgentZipSha256` parameter verifies the downloaded agent.zip before extraction.
Bot invite command now emits a download-then-execute pattern instead of `irm | iex`.

### 2. ~~Invite Expiration Policy~~ ✅
`InviteCreate.expiresInHours` defaults to 24, enforced range 1–168 (7 days max) via Pydantic `Field`.
Registration route always computes `expires_at`. Bot validates the range before calling the API.
`bot-guide.md` updated — "never expires" behavior removed.

### 3. ~~Mission File Handling — Path and Size Hardening~~ ✅
`agent/security.py` added: `sanitize_miz_filename()` rejects traversal sequences, path separators, non-.miz extensions, and oversized names. `safe_join()` resolves and bounds-checks the final path.
Applied to all upload, download, and delete endpoints in `agent/api/routes/instances.py`.
`max_upload_bytes` (default 100 MB) added to `AgentConfig`; upload routes return 413 on oversize.

### 4. ~~Log Bundle Redaction~~ ✅
`_SECRET_PATTERNS` and `redact_line()` added to `agent/controller.py`.
Applied to both `lines` and `scripting_errors` in the `logs_bundle` action before storing in job result.

### 8. ~~Destructive Command Confirmation Coverage~~ ✅
`/dcs resetpersist` now uses `_ConfirmView` (ephemeral, 30s timeout) matching reboot/delete pattern.
`bot-guide.md` updated to document the confirmation requirement.

---

### 5. ~~Replay Protection / Identity Hardening~~ ✅
`orchestrator/agent_client.py`: `_sign_headers()` generates `X-Timestamp`, `X-Nonce`, `X-Signature` (HMAC-SHA256 over `METHOD\npath\ntimestamp\nnonce`) on every outgoing request to the agent.
`agent/api/auth.py`: `require_api_key` validates timestamp skew ≤ 60s, HMAC signature, and nonce freshness via `NonceStore`. Signing headers are optional — presence triggers full enforcement (dev clients without signing still work if API key is correct).
`agent/api/app.py`: `NonceStore` instance attached to `app.state.nonce_store`.

### 6. ~~Rate Limiting and Auth Abuse Controls~~ ✅
`_FailedAuthTracker` added to both `agent/api/auth.py` and `orchestrator/api/auth.py`.
5 failed attempts from the same IP within 5 minutes → 429 lockout for 5 minutes.
Uses `hmac.compare_digest` for timing-safe key comparison on both apps.

### 7. ~~Audit Logging Durability~~ ✅
`audit_logs` table added to orchestrator SQLite DB (`orchestrator/database.py`).
`orchestrator/api/routes/actions.py`: reads `X-Discord-User-Id` header, stores actor on `Job`, writes audit rows at queued + all terminal states.
`orchestrator/jobs.py`: `actor` field added to `Job` and `JobStore.create()`.
`discord-bot/orchestrator_client.py`: `trigger_action()` accepts `actor_id` and passes `X-Discord-User-Id` header.
`discord-bot/cogs/dcs.py`: all 10 `trigger_action` call sites pass `str(interaction.user.id)` (or `"system"` for scheduler auto-restarts).

---

## All items resolved ✅
