# Scripts

PowerShell dev and test helpers for the DCS platform.

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
