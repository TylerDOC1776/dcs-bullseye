# dcs-platform

DCS World server management system — monorepo workspace.

## Structure

| Directory | Status | Description |
|-----------|--------|-------------|
| `orchestrator/` | Scaffold | FastAPI orchestrator (command router, RBAC, jobs, SSE/WebSocket) |
| `agent/` | Scaffold | FastAPI agent (Windows node: process control, logs, missions) |
| `discord-bot/` | Scaffold | DCS management Discord bot |
| `music-bot/` | **Active** | Working Discord music bot (Python + discord.py) |
| `archive/` | Archived | Python prototype (hub-and-spoke) + legacy DCSAdminBot |
| `docs/` | Reference | API specs, architecture docs, design notes |
| `configs/` | — | Config file examples |
| `scripts/` | — | Dev/build/test scripts |

## Docs

- `docs/OpenAPI.yaml` — Full REST API contract (source of truth)
- `docs/architecture.md` — System architecture overview
- `docs/notes.md` — FastAPI/NSSM notes and target monorepo structure

## Quick Reference

### Music Bot (active)
```bash
cd music-bot
pip install -r requirements.txt
# configure .env from .env.example
python bot.py
```

### Archived prototype (reference only)
```bash
cd archive
pip install -r requirements.txt
python -m hub.server
```

See `CLAUDE.md` for full details on all packages and conventions.
