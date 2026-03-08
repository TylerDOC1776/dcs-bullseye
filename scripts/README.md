# Scripts

Deployment installers and dev/test helpers for the DCS platform.

## `install-vps.sh` — VPS installer (Linux)

Sets up the full platform on a fresh Debian/Ubuntu VPS: orchestrator, Discord bot, frp server, systemd services, and the static install files served to community hosts.

```bash
# Fresh install (interactive — will prompt for Discord config and public URL)
bash install-vps.sh

# Update existing install (pull latest code, rebuild agent.zip, restart services)
bash install-vps.sh --update
```

See the [VPS Setup wiki page](https://github.com/TylerDOC1776/dcs-bullseye/wiki/VPS-Setup) for full details.

---

## `install-agent.ps1` — Windows agent installer

Installs the DCS Agent on a Windows DCS machine and registers it with the orchestrator. Requires an invite code generated via `/dcs invite` in Discord.

```powershell
# Fresh install
.\install-agent.ps1 -InviteCode XXXX-XXXX-XXXX-XXXX -OrchestratorUrl https://your-orchestrator-url

# Update existing install
.\install-agent.ps1 -Update
```

This script is served automatically at `<ORCHESTRATOR_URL>/install/install.ps1` after the VPS is set up. Community hosts receive the full one-liner from the admin via `/dcs invite`.

---

## `dev.ps1` — Start services in dev mode

Launches the orchestrator and Discord bot in separate terminal windows.

```powershell
# Start orchestrator + Discord bot (default config)
.\scripts\dev.ps1

# Custom orchestrator config
.\scripts\dev.ps1 -OrchestratorConfig C:\configs\my-orchestrator.json

# Also start a local agent instance
.\scripts\dev.ps1 -IncludeAgent
```

**Prerequisites:**
- `discord-bot/.env` populated (copy from `.env.example`)
- Orchestrator config file exists (see `configs/orchestrator.example.json`)
- Python env with dependencies installed in each package directory

## `test.ps1` — Run test suites

Runs `pytest tests/` in `agent/` and `orchestrator/`.

```powershell
# Run all tests
.\scripts\test.ps1

# Run only agent tests (verbose)
.\scripts\test.ps1 -Package agent -Verbose

# Run only orchestrator tests
.\scripts\test.ps1 -Package orchestrator
```

**Prerequisites:**
```powershell
pip install -r agent/requirements-test.txt
pip install -r orchestrator/requirements-test.txt
```

Exits with code 1 if any suite fails.
