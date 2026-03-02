# Archive — Python Prototype

This directory contains the archived Python prototype of the DCS server management system (previously at `DCSBot2.0/NewDCSBot/`).

## Contents

- `hub/` — FastAPI hub server + Discord bot (`src/hub/` from prototype)
- `node/` — Windows node agent service (`src/node/` from prototype)
- `tests/` — pytest test suite
- `requirements.txt` — Python dependencies
- `old-bot/` — Legacy DCSAdminBot code (previously at `DCSBot2.0/Old Code/`)

## Status

**Archived — not actively developed.** The new implementation will live in `orchestrator/`, `agent/`, and `discord-bot/` at the repo root. See `docs/OpenAPI.yaml` for the target API contract.

## Running (historical reference)

```bash
# From this directory, with virtualenv activated:
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt

# Hub API server
python -m hub.server

# Discord bot (requires .env)
python -m hub.bot

# Node agent (Windows only)
python -m node_service.service

# Tests
pytest tests/
```
