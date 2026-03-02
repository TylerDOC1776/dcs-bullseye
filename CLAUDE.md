# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo Structure

```
dcs-platform/
├── archive/          — Archived Python prototype (hub-and-spoke bot)
├── docs/             — All spec and design docs
├── orchestrator/     — New FastAPI orchestrator (scaffold, not yet implemented)
├── agent/            — New FastAPI agent for Windows nodes (scaffold)
├── discord-bot/      — New DCS Discord bot (scaffold)
├── music-bot/        — Working music bot (Python + discord.py, active)
├── configs/          — Config examples
├── scripts/          — Dev/build/test scripts
├── README.md
└── CLAUDE.md
```

## Docs (`docs/`)

All specification and design documents live here:

| File | Contents |
|------|----------|
| `docs/OpenAPI.yaml` | Full REST API spec (Orchestrator + Agent) — **source of truth** |
| `docs/Orchestrator.yaml` | SSE/WebSocket event endpoint additions |
| `docs/schemas.yaml` | RBAC roles and scope definitions |
| `docs/architecture.md` | Hub-and-spoke architecture design |
| `docs/adaptive-defense.md` | ADS — DCS mission Lua scripting spec |
| `docs/installer.md` | Community host installer spec |
| `docs/goonfront.md` | Goonfront campaign design |
| `docs/benchmarking.md` | Docker vs native benchmark harness design |
| `docs/tts-voice.md` | Voice/TTS Discord feature design notes |
| `docs/notes.md` | FastAPI/NSSM notes + target monorepo structure |

When implementing new API endpoints or features, refer to `docs/OpenAPI.yaml` as the source of truth for schemas, auth patterns, and operation IDs.

Key API design decisions:
- Long-running actions are **Jobs** (async, poll for completion)
- Real-time notifications via **SSE** (`/events/stream`) or **WebSocket** (`/events/ws`)
- RBAC with three roles (`viewer`, `operator`, `admin`) and fine-grained scopes
- Two server bases: Orchestrator (public edge) and Agent (internal node)
- Tailscale used for VPS ↔ node networking behind CGNAT

## Archived Python Prototype (`archive/`)

The original Python implementation is preserved here for reference. **Not actively developed.**

```
archive/
├── hub/              — FastAPI hub server + Discord bot (was src/hub/)
├── node/             — Windows node agent (was src/node/)
├── tests/            — pytest test suite
├── requirements.txt
└── old-bot/          — Legacy DCSAdminBot (pre-rewrite)
```

### Architecture (reference)

**Hub-and-spoke**: Central FastAPI server (VPS) + Discord bot manages Windows node agents on DCS machines.

**Command flow**: Discord → hub API → CommandStore → node polls → DcsController executes → node ACKs → Discord reply

**Hub** (`archive/hub/`): `api.py`, `server.py`, `bot.py`, `store.py`, `hub_client.py`, `config.py`, `bot_config.py`

**Node** (`archive/node/node_service/`): `service.py` (win32serviceutil), `controller.py` (psutil), `comm.py`, `config.py`, `logs.py`, `missions.py`. GUI panel in `archive/node/node_ui/`.

**Tests**: `archive/tests/conftest.py` adds `src/` to sys.path. Mirror module names.

### Running archived code (historical reference)

```bash
cd archive
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python -m hub.server      # hub API
python -m hub.bot         # Discord bot
python -m node_service.service  # node agent (Windows)
pytest tests/
```

## Music Bot (`music-bot/`)

Working Discord music bot. Python + discord.py. **Active code — keep intact.**

```
music-bot/
├── bot.py
├── cogs/             — music.py, playlists.py
├── src/              — deploy-commands.js, index.js
├── music_queue.py
├── playlist_manager.py
├── requirements.txt
├── package.json
└── .env.example
```

## New Package Scaffolds

These directories are stubs for the future TypeScript/Python implementation:

| Directory | Purpose |
|-----------|---------|
| `orchestrator/` | FastAPI orchestrator — replaces archive/hub. See `docs/OpenAPI.yaml`. |
| `agent/` | FastAPI agent (NSSM on Windows) — replaces archive/node. See `docs/OpenAPI.yaml`. |
| `discord-bot/` | DCS Discord bot — replaces archive/hub/bot.py. |
| `configs/` | Config examples for all packages |
| `scripts/` | Dev/build/test scripts |

## Coding Conventions (for new code)

- Python 3.11+, asyncio, type annotations throughout
- 4-space indentation, `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants
- Validate Discord command arguments against instance names in config before any disk/process operations
