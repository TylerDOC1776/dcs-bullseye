# dcs-platform

DCS World server management system — monorepo workspace.

## Structure

| Directory | Status | Description |
|-----------|--------|-------------|
| `orchestrator/` | Active | FastAPI orchestrator (command router, auth, jobs, audit logging) |
| `agent/` | Active | FastAPI agent (Windows node: process control, logs, missions) |
| `discord-bot/` | Active | DCS management Discord bot |
| `archive/` | Archived | Python prototype (hub-and-spoke) + legacy DCSAdminBot |
| `docs/` | Reference | API specs, architecture docs, design notes |
| `configs/` | — | Config file examples |
| `scripts/` | — | Dev/build/test scripts |

## Docs

- `docs/OpenAPI.yaml` — Full REST API contract (source of truth)
- `docs/architecture.md` — System architecture overview
- `docs/network-overview.md` — Tunnel and connectivity diagram

## Quick Reference

### Orchestrator
```bash
cd orchestrator
pip install -r requirements.txt
export DCS_ORCHESTRATOR_CONFIG=../configs/orchestrator.example.json
python -m orchestrator serve
```

### Agent (Windows)
```bash
cd agent
pip install -r requirements.txt
# configure C:\ProgramData\DCSAgent\config.json
python -m agent serve
```

### Archived prototype (reference only)
```bash
cd archive
pip install -r requirements.txt
python -m hub.server
```

See `CLAUDE.md` for full details on all packages and conventions.
