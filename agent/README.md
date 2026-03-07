# Agent

FastAPI agent that runs under NSSM on Windows DCS server machines. Replaces the archived node service. Handles DCS process control, log collection, and mission deployment; communicates with the orchestrator over an frp reverse tunnel.

See `docs/OpenAPI.yaml` for the full API contract and `docs/network-overview.md` for architecture context.

## Status

CLI + NSSM service management implemented. REST API layer implemented (`agent/api/`).

---

## Package Layout

```
agent/
├── __init__.py
├── __main__.py       — python -m agent entry point
├── config.py         — dataclasses + JSON loader
├── nssm.py           — thin subprocess wrapper around nssm.exe
├── controller.py     — high-level per-instance operations
├── analytics.py      — background reporter: polls DCS, pushes events to orchestrator
├── cli.py            — argparse CLI (includes `serve` subcommand)
├── jobs.py           — in-memory async job store
├── server.py         — uvicorn entry point
├── requirements.txt  — fastapi, uvicorn, aiohttp
└── api/
    ├── app.py        — FastAPI application factory
    ├── auth.py       — X-API-Key authentication dependency
    ├── models.py     — Pydantic response models
    └── routes/
        ├── health.py        — GET /health (unauthenticated)
        ├── capabilities.py  — GET /agent/v1/capabilities
        ├── instances.py     — GET /agent/v1/instances[/{id}/status]
        ├── actions.py       — POST /agent/v1/instances/{id}/actions/{action}
        └── jobs.py          — GET /agent/v1/jobs/{jobId}
```

---

## Prerequisites

- Python 3.11+
- [NSSM](https://nssm.cc/) — either on `PATH` or set `nssm_path` in config
- Run as **Administrator** when installing/removing services

---

## Quick Start

### 1. Create a config file

Copy the example and fill in your real paths:

```
copy configs\agent.example.json C:\ProgramData\DCSAgent\config.json
```

Edit `config.json`:
- Set `exe_path` to your `DCS_server.exe` location
- Set `saved_games_key` to match each instance's Saved Games folder name
- Set `log_path` to each instance's `dcs.log`
- Set `missions_dir` to each instance's Missions folder
- Set `nssm_path` if nssm.exe is not on PATH
- Set `orchestrator_url` to your orchestrator's public URL (e.g. `https://goon.gsquad.cc`) — enables analytics reporting
- Set `host_id` to the host ID assigned during registration — required for analytics

### 2. Point the env var at your config (optional)

```powershell
$env:DCS_AGENT_CONFIG = "C:\ProgramData\DCSAgent\config.json"
```

Or pass `--config <path>` to any command.

---

## CLI Reference

All commands accept either an instance **name** (e.g. `"Server 1"`) or its
**service_name** (e.g. `DCS-server1`), case-insensitive.

```
python -m agent --help
python -m agent <command> --help
```

### Install services (run as Administrator)

```powershell
# Install all three instances
python -m agent install --all

# Install a single instance
python -m agent install "Server 1"
```

### Check status

```powershell
python -m agent status
```

Output:
```
Name        Service       Status
----------  ------------  ---------------
Server 1    DCS-server1   SERVICE_RUNNING
Server 2    DCS-server2   SERVICE_STOPPED
Server 3    DCS-server3   SERVICE_RUNNING
```

### Start / Stop / Restart

```powershell
python -m agent start  "Server 1"
python -m agent stop   DCS-server2
python -m agent restart --all
```

### Tail logs

```powershell
# Last 50 lines (default)
python -m agent logs "Server 1"

# Last 100 lines
python -m agent logs DCS-server1 --lines 100
```

### Remove services

```powershell
python -m agent remove --all
```

---

## Service Configuration Details

When `install` runs, the following NSSM parameters are set automatically:

| Parameter         | Value |
|-------------------|-------|
| `AppParameters`   | `-w <saved_games_key>` |
| `AppDirectory`    | Directory containing `DCS_server.exe` |
| `Description`     | `DCS World — <instance name>` |
| `Start`           | `SERVICE_AUTO_START` if `auto_start: true`, else `SERVICE_DEMAND_START` |
| `AppStdout`       | `<log_dir>\<service_name>.log` |
| `AppStderr`       | `<log_dir>\<service_name>.log` |
| `AppRotateFiles`  | `1` (daily rotation at 86400 s) |
| `ObjectName`      | Current Windows user (needed for Saved Games path access) |

> **Note:** The installer must be run as the same user that owns the Saved Games
> folder (or as an admin who sets explicit credentials). DCS reads mission and
> configuration files from `%USERPROFILE%\Saved Games\<key>\`, so the service
> must run as that user to resolve those paths correctly.

---

## REST API

The agent exposes a FastAPI HTTP server on `host:port` (default `0.0.0.0:8787`).
All endpoints except `/health` require the `X-API-Key` header.

### Start the server

```powershell
pip install fastapi "uvicorn[standard]"
$env:DCS_AGENT_CONFIG = "configs\agent.example.json"

python -m agent serve
# Override host/port without editing config:
python -m agent serve --host 127.0.0.1 --port 9000
```

To run the server itself as a persistent Windows service, install it with NSSM:

```powershell
nssm install DCSAgentAPI python -m agent serve
nssm set DCSAgentAPI AppDirectory C:\path\to\dcs-platform
nssm start DCSAgentAPI
```

### Authentication

Pass `X-API-Key: <your-key>` on every request except `/health`.
Set `api_key` in `config.json` (or `configs/agent.example.json`).
Empty `api_key` disables auth (dev mode — a warning is logged at startup).

### Endpoint Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Heartbeat / NSSM probe |
| `GET` | `/agent/v1/capabilities` | Yes | OS info + supported actions |
| `GET` | `/agent/v1/instances` | Yes | List instances with status |
| `GET` | `/agent/v1/instances/{instanceId}/status` | Yes | Runtime status for one instance |
| `POST` | `/agent/v1/instances/{instanceId}/actions/{action}` | Yes | Trigger async action → 202 + jobId |
| `GET` | `/agent/v1/jobs/{jobId}` | Yes | Poll job status |

`instanceId` = `service_name` (e.g. `DCS-server1`), or the human `name` (case-insensitive).

Supported `action` values: `start`, `stop`, `restart`, `logs_bundle`, `mission_load`, `minimize_window`, `reset_persist`, `set_password`.

### Example Usage

```powershell
# Health check (no auth)
curl http://localhost:8787/health

# Capabilities
curl -H "X-API-Key: change-me" http://localhost:8787/agent/v1/capabilities

# List instances
curl -H "X-API-Key: change-me" http://localhost:8787/agent/v1/instances

# Instance status
curl -H "X-API-Key: change-me" http://localhost:8787/agent/v1/instances/DCS-server1/status

# Trigger start → returns jobId
curl -X POST -H "X-API-Key: change-me" http://localhost:8787/agent/v1/instances/DCS-server1/actions/start

# Poll job
curl -H "X-API-Key: change-me" http://localhost:8787/agent/v1/jobs/job_a1b2c3d4e5f6

# logs_bundle (no NSSM — reads the DCS log file)
curl -X POST -H "X-API-Key: change-me" http://localhost:8787/agent/v1/instances/DCS-server1/actions/logs_bundle

# Error cases
curl -X POST -H "X-API-Key: change-me" http://localhost:8787/agent/v1/instances/DCS-server1/actions/explode
# → 400 (unknown action)
curl -H "X-API-Key: change-me" http://localhost:8787/agent/v1/instances/doesnotexist/status
# → 404
curl http://localhost:8787/agent/v1/instances
# → 403 (missing key)
```

Interactive API docs: `http://localhost:8787/agent/v1/docs`

---

## Verification Checklist

After `install --all`:

1. Open `services.msc` — confirm all three services appear
2. Check Start Type = **Automatic** (for instances with `auto_start: true`)
3. Run `python -m agent status` — should show `SERVICE_STOPPED` (not yet started)
4. Run `python -m agent start --all` — then status should show `SERVICE_RUNNING`
5. Run `python -m agent logs "Server 1"` — confirm DCS log output appears
6. Reboot the machine — services should auto-start
