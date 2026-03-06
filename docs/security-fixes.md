# DCS Security Remediation Guide

## Status Summary

| # | Issue | Status |
|---|-------|--------|
| 1 | Installer HTTPS + hash verification | ✅ Done |
| 2 | Invite TTL required + max cap | ✅ Done |
| 3 | Mission filename/path hardening + upload size cap | ✅ Done |
| 4 | Log redaction | ✅ Done |
| 8 | resetpersist confirmation | ✅ Done |
| 5 | Replay protection / request signing | ✅ Done |
| 6 | Rate limiting + failed-auth lockout | ✅ Done |
| 7 | Durable audit logging | ✅ Done |

---

## Completed

### 1) Installer HTTPS + hash verification ✅

**Changes made:**
- `scripts/install-agent.ps1`: Added required `$OrchestratorUrl` parameter. Removed hardcoded `http://` constant. HTTPS enforced with `throw` on HTTP URLs. Added optional `$AgentZipSha256` parameter with `Assert-Sha256` verification before extraction. Applies in both install and update modes.
- `discord-bot/config.py`: Added `agent_zip_sha256` field (env: `AGENT_ZIP_SHA256`).
- `discord-bot/cogs/dcs.py`: Invite one-liner changed from `irm | iex` to download-to-file then `-File` execution. Passes `-OrchestratorUrl` and `-AgentZipSha256` (if configured).
- `docs/community-host-setup.md`: Updated example commands to use new pattern with HTTPS placeholder.

**Deploy notes:**
- Set `INSTALLER_BASE_URL` to your HTTPS public URL (e.g. `https://your-domain.com`)
- Build and hash your `agent.zip`, set `AGENT_ZIP_SHA256` to the SHA-256 of the zip
- Update hash in env whenever you publish a new agent release

---

### 2) Invite TTL required + max cap ✅

**Changes made:**
- `orchestrator/api/models.py`: `InviteCreate.expiresInHours` is now `Field(default=24, ge=1, le=168)` — never nullable.
- `orchestrator/api/routes/registration.py`: Always computes `expires_at` (removed optional branch).
- `discord-bot/cogs/dcs.py`: `expires_in_hours` defaults to 24, validated 1–168 before API call. "Never" embed field removed.
- `docs/bot-guide.md`: Updated invite description to reflect 24h default and 7-day cap.

---

### 3) Mission filename/path hardening + upload size cap ✅

**Changes made:**
- `agent/security.py` (new): `sanitize_miz_filename()` — rejects empty, >255 chars, path separators, `..`, non-.miz. `safe_join()` — resolves path and verifies it stays inside root.
- `agent/api/routes/instances.py`: All 5 file endpoints (instance upload, instance delete, active download, active upload, active delete) now call `sanitize_miz_filename` and `safe_join` before any path operation. Upload endpoints return HTTP 413 if body exceeds `max_upload_bytes`.
- `agent/config.py`: `max_upload_bytes` field added (default 100 MB, JSON-configurable).

---

### 4) Log redaction ✅

**Changes made:**
- `agent/controller.py`: `_SECRET_PATTERNS` list (matches api_key/token/password/secret/authorization/x-api-key patterns). `_redact_match()` and `redact_line()` functions added at module level.
- `agent/api/routes/actions.py`: `logs_bundle` branch applies `redact_line` to every entry in `lines` and `scripting_errors` before assigning to `job.result`.

---

### 8) Consistent confirmation for destructive commands ✅

**Changes made:**
- `discord-bot/cogs/dcs.py`: `/dcs resetpersist` now shows `_ConfirmView` (ephemeral, 30s timeout) before triggering the action. Matches the reboot/delete pattern exactly.
- `docs/bot-guide.md`: `resetpersist` description updated to note confirmation. Notes section updated to include resetpersist alongside reboot and delete.

---

### 5) Replay protection + request signing ✅

**Changes made:**
- `orchestrator/agent_client.py`: `_sign_headers(method, path)` generates `X-Timestamp` (unix epoch), `X-Nonce` (32-hex random), `X-Signature` (HMAC-SHA256 over `METHOD\npath\ntimestamp\nnonce` keyed by `api_key`). Applied to all `_get`, `_post`, `_delete`, upload, and download methods.
- `agent/api/auth.py`: `require_api_key` validates timestamp skew ≤ 60s, HMAC, and nonce freshness via `NonceStore`. Signing is optional — if any signing header is present all three are enforced.
- `agent/api/app.py`: `NonceStore` instance attached to `app.state.nonce_store` at startup.

---

### 6) Rate limiting + failed-auth lockout ✅

**Changes made:**
- `_FailedAuthTracker` added to both `agent/api/auth.py` and `orchestrator/api/auth.py`.
- Policy: 5 failures from the same IP within 5 minutes → 429 lockout for 5 minutes.
- Both apps now use `hmac.compare_digest` for timing-safe key comparison.
- Successful auth clears the failure record for that IP.

---

### 7) Durable audit logging ✅

**Changes made:**
- `orchestrator/database.py`: `audit_logs` table added (id, timestamp, actor, action, instance_id, host_id, job_id, status, detail). `write_audit_log()` and `list_audit_logs()` methods added. Table is created on connect alongside other tables.
- `orchestrator/jobs.py`: `actor: str | None` field added to `Job` dataclass and `JobStore.create()`.
- `orchestrator/api/routes/actions.py`: Reads `X-Discord-User-Id` request header as actor. Writes audit row at job queued and at every terminal state (succeeded/failed/timeout). `db` passed into `_run_action` background task.
- `discord-bot/orchestrator_client.py`: `trigger_action()` accepts `actor_id: str | None` and passes it as `X-Discord-User-Id` header.
- `discord-bot/cogs/dcs.py`: All 10 `trigger_action` call sites pass `str(interaction.user.id)`. Auto-restart (scheduler) passes `"system"`.

---

## Quick Test Checklist (completed items)

- [ ] Invite command rejects TTL outside 1..168
- [ ] Installer throws on non-HTTPS OrchestratorUrl
- [ ] Installer verifies agent.zip hash when AgentZipSha256 is provided
- [ ] Upload/download/delete reject traversal payloads (`../`, `..\`, absolute paths)
- [ ] Upload larger than max_upload_bytes returns HTTP 413
- [ ] Log bundle output redacts token/password/api_key patterns
- [ ] `/dcs resetpersist` shows confirmation before executing
- [ ] Agent rejects request with timestamp skew > 60s (403)
- [ ] Agent rejects replayed nonce (403)
- [ ] Agent rejects invalid HMAC signature (403)
- [ ] 5 bad API key attempts → 429 lockout; clears after 5 min
- [ ] Bot commands write actor ID to orchestrator audit_logs table
- [ ] Auto-restart writes actor "system" to audit_logs
