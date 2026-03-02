# Windows Node Agent (Design Notes)

## Responsibilities
- Manage DCS server instances on a Windows host (start/stop/restart/update).
- Monitor processes/logs, cache log bundles, and respond to fetch requests from the VPS bot.
- Maintain secure outbound connection to the orchestration API (HTTPS/WebSocket) for commands + telemetry.
- Provide a local admin experience (service + GUI config) so operators can change settings without editing files manually.

## Proposed Components
| Component | Tech | Purpose |
|-----------|------|---------|
| `NodeService` | Python 3.11 + PyInstaller (or .NET) | Windows service running with elevated rights. Handles command execution, process control, log packaging, and heartbeats. Exposes a local named-pipe/HTTP endpoint for the config UI. |
| `NodeUI` | PySide6 / WinUI (via pythonnet) | Tray/config app launched on demand. Reads/writes `%ProgramData%\DCSAdminNode\config.json`, validates inputs, and restarts the service if needed. |
| `Installer` | PowerShell bootstrap + MSI | Downloads signed binaries, installs dependencies, registers service (LocalSystem), and runs first-run wizard. |
| `AgentAPI` | REST/gRPC schema | Defines command payloads (`start_instance`, `fetch_logs`), responses, auth headers, and heartbeat messages. Shared with the VPS bot for code generation. |

## Configuration Schema (Draft)
```json
// see src/node/example_config.json for a template
```

### Required fields
- `node_id`: unique identifier for the machine (used in heartbeats/logging).
- `role`: one of `server`, `standalone`, or `slave`; influences what commands are allowed.
- `vps_endpoint`: HTTPS base URL for the central orchestration API (required when `command_transport` = `http`).
- `api_key` / `api_key_file` / `api_key_env`: specify the node credential inline, via a file path, or by referencing an environment variable (only one is required). File/env values are trimmed at load, so secrets never need to live in plaintext JSON.
- `instances`: list of objects containing:
  - `cmd_key`: short lowercase identifier used in commands (e.g., `southern`).
  - `name`: actual DCS window/server name (passed to `-w` flag).
  - `exe_path`, `log_path`: absolute paths for the DCS binary and main log.
  - `missions_dir` (optional): destination for mission uploads (needed for remote deploys if not provided per command).
- Optional tuning knobs:
  - `heartbeat_interval` (default 30s) and `command_poll_interval` (default 5s).
  - `command_transport`: `filesystem` (default, watches `%ProgramData%\DCSAdminNode\commands`) or `http` to poll the VPS API.
  - `command_queue_dir`: override the folder watched when using `filesystem` transport.
  - `log_bundle_dir` & `log_bundle_max_lines`: control where `collect_logs` writes and how many lines are tailed from each log file.
  - Future fields like `log_bundle` retention will live alongside these.

## Service Workflow
1. Bootstrap: load config, register with VPS via `/api/nodes/register`.
2. Start heartbeat task (status + per-instance state), posting to the hub API whenever the node uses HTTP transport.
3. Listen for commands (pull via filesystem queue or HTTP). Commands include:
   - `start_instance`, `stop_instance`, `restart_instance`
   - `deploy_miz`, `update_password`
   - `collect_logs` (zip + upload or stream)
4. Execute PowerShell helpers (`DCSManage.ps1` equivalent) with strict allowlists.
5. Emit audit logs to both local file and VPS.

## Immediate TODOs
- [ ] Finalize transport choice (REST with long-poll vs WebSocket vs gRPC).
- [ ] Define command/response schema and error codes.
- [x] Prototype Windows service skeleton (Python `win32serviceutil` or `pywin32`).
- [ ] Evaluate packaging path (PyInstaller vs .NET rewrite).
- [ ] Draft PowerShell installer script (`Install-DcsNode.ps1`) to download and install the agent.

## Python Service Skeleton

- Package: `node_service`
  - `config.py` loads `%ProgramData%\DCSAdminNode\config.json` and validates instances.
  - `controller.py` exposes `start_instance/stop_instance/restart_instance` and a CLI replacement for the old restart EXE: `python -m node_service.controller restart southern`.
  - `service.py` contains the Windows-service wrapper (`NodeWindowsService`) and the cross-platform async runner for development.
- To install the service on Windows (after installing dependencies: `pip install pywin32 psutil`):
  ```powershell
  python -m node_service.service install
  python -m node_service.service start
  ```
  Running the module directly (`python -m node_service.service`) falls back to a console loop for testing outside Windows.

### Command Queue / HTTP Transport
- Default mode watches `%ProgramData%\DCSAdminNode\commands` for JSON files:
  ```json
  {
    "id": "cmd-001",
    "action": "restart",
    "instance": "southern"
  }
  ```
- Switch `"action"` to `deploy_mission` with params like `{"filename": "Op.e.miz", "content_b64": "<...>"}` to push missions, or `collect_logs` with `{"lines": 2000}` to request a log bundle. See `node_service.missions` and `node_service.logs`.
- Set `"command_transport": "http"` plus your `vps_endpoint` to trade the filesystem queue for HTTPS polling. The node posts `Authorization: Bearer <api_key>` headers and acknowledges completions back to `/api/nodes/<node_id>/commands/<id>/ack`.
- Regardless of transport, the service logs every heartbeat and command result, making it easy to audit remote actions. When using HTTP transport the node also POSTs `/heartbeat` plus uploads log bundles directly to the hub after each `collect_logs` command so Discord operators can download them remotely.

## Config UI

- Launch the GUI editor with `python -m node.node_ui.app`. It loads `%ProgramData%\DCSAdminNode\config.json` (or browse to another file) and presents tabs for connection/auth, instance definitions, and log/command paths.
- The tool enforces lowercase `cmd_key` values, validates required fields, and supports inline API keys, key files, or environment variable references. Hit **Save** to write JSON back to disk; folders are created automatically if they don't exist.

## Installer Bootstrap

- Run `scripts/Install-DcsNode.ps1` (elevated) on a Windows host to copy the node packages into `C:\Program Files\DCSAdminNode`, create a dedicated virtual environment, install Python dependencies, and seed `%ProgramData%\DCSAdminNode\config.json` from `example_config.json` if needed.
- The script now installs/starts the Windows service (`DCSNodeService`) automatically; add `-SkipService` if you only want to stage files without touching the service.
- Pass `-LaunchConfigUI` to open the PySide6 editor immediately after bootstrapping. Rerun the script any time you need to refresh dependencies or reinstall service assets.
