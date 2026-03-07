# DCS Orchestrator

FastAPI hub server that registers DCS agent nodes, stores host/instance metadata in SQLite, and proxies instance operations to agent APIs.

See `docs/OpenAPI.yaml` for the full API contract and `docs/architecture.md` for design context.

**Status:** Implemented — config, DB layer, agent client, auth, all routes, and CLI serve entry point complete.

---

## Package Layout

```
orchestrator/
├── __init__.py
├── __main__.py          # python -m orchestrator entry point
├── cli.py               # argparse CLI
├── config.py            # OrchestratorConfig dataclass + JSON loader
├── database.py          # aiosqlite Database class (hosts, instances, analytics)
├── jobs.py              # In-memory JobStore
├── events.py            # EventBus for SSE broadcasting
├── agent_client.py      # Async httpx wrapper for agent APIs
├── server.py            # uvicorn.run() wrapper
├── requirements.txt
└── api/
    ├── app.py           # FastAPI factory (create_app)
    ├── auth.py          # X-API-Key dependency
    ├── models.py        # Pydantic models
    └── routes/
        ├── health.py       # GET /health
        ├── hosts.py        # CRUD + proxy health
        ├── instances.py    # CRUD + live status
        ├── actions.py      # POST action → async job
        ├── jobs.py         # GET jobs / GET jobs/{id}
        ├── events.py       # SSE stream + WebSocket
        ├── analytics.py    # POST (agent push) + GET (admin query) analytics events
        └── registration.py # Community host self-registration with invite codes
```

---

## Quick Start

```powershell
cd orchestrator
pip install -r requirements.txt

# Point at example config (edit api_key first)
$env:DCS_ORCHESTRATOR_CONFIG = "..\configs\orchestrator.example.json"

python -m orchestrator serve
# → http://0.0.0.0:8888
```

CLI flags override config:

```powershell
python -m orchestrator serve --host 127.0.0.1 --port 9000
```

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Orchestrator health (DB probe) |
| GET | `/api/v1/hosts` | Yes | List registered hosts |
| POST | `/api/v1/hosts` | Yes | Register a new agent host |
| GET | `/api/v1/hosts/{hostId}` | Yes | Get host by ID |
| PATCH | `/api/v1/hosts/{hostId}` | Yes | Update host fields |
| GET | `/api/v1/hosts/{hostId}/health` | Yes | Proxy health check to agent |
| GET | `/api/v1/instances` | Yes | List instances with live status |
| POST | `/api/v1/instances` | Yes | Register an instance |
| GET | `/api/v1/instances/{instanceId}` | Yes | Get instance by ID |
| GET | `/api/v1/instances/{instanceId}/status` | Yes | Live runtime status (proxied) |
| POST | `/api/v1/instances/{instanceId}/actions/{action}` | Yes | Trigger async action |
| GET | `/api/v1/jobs` | Yes | List jobs (`?status=` filter) |
| GET | `/api/v1/jobs/{jobId}` | Yes | Poll job status |
| GET | `/api/v1/events/stream` | Yes | SSE event stream (status changes, job failures) |
| POST | `/api/v1/analytics/events` | Agent key | Ingest analytics events from agents |
| GET | `/api/v1/analytics/events` | Yes | Query stored analytics events |
| POST | `/api/v1/register` | Invite code | Community host self-registration |
| POST | `/api/v1/invites` | Yes | Generate a community host invite code |

Swagger UI: `http://localhost:8888/api/v1/docs`

---

## Auth

All `/api/v1/*` routes require `X-API-Key: <your-key>` header.

If `api_key` is empty in config, auth is disabled (dev mode — a warning is logged).

---

## Config (`configs/orchestrator.example.json`)

```json
{
  "api_key": "change-me",
  "host": "0.0.0.0",
  "port": 8888,
  "db_path": "C:\\ProgramData\\DCSOrchestrator\\orchestrator.db",
  "log_level": "info"
}
```

Set `DCS_ORCHESTRATOR_CONFIG` env var to the config file path, or pass `--config PATH` to the CLI.

---

## Agent URL Convention

When registering a host, `agentUrl` should be the agent's **root** URL (no `/agent/v1`):

```
http://100.x.x.x:8787
```

The orchestrator appends `/agent/v1` internally when calling agent endpoints.
