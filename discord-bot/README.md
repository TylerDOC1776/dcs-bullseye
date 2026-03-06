# DCS Discord Bot

Discord slash-command interface for managing DCS World server instances via the orchestrator API.
Replaces `archive/hub/bot.py`. Each command is grouped under `/dcs`.

## Commands

| Command | Auth | Description |
|---------|------|-------------|
| `/dcs status [instance]` | channel | All instances or one detailed status |
| `/dcs start <instance>` | channel + role | Start instance (polls job to completion) |
| `/dcs stop <instance>` | channel + role | Stop instance |
| `/dcs restart <instance>` | channel + role | Restart instance |
| `/dcs logs <instance>` | channel | Fetch log bundle (file or code block) |
| `/dcs hosts` | channel | List registered hosts |
| `/dcs jobs [status]` | channel | Last 10 jobs with optional status filter |

Instance arguments use autocomplete — available instances are fetched live from the orchestrator.

## Setup

```bash
cd discord-bot
python -m venv .venv
.venv/Scripts/activate       # Windows
pip install -r requirements.txt

cp .env.example .env
# Fill in DISCORD_TOKEN, GUILD_ID, ORCHESTRATOR_URL
```

### Required env vars

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Bot token from Discord Developer Portal |
| `GUILD_ID` | Server (guild) ID — commands synced here |
| `ORCHESTRATOR_URL` | Base URL of the orchestrator (e.g. `http://localhost:8888`) |
| `ORCHESTRATOR_API_KEY` | API key set in orchestrator config |
| `BOT_CHANNEL_ID` | *(optional)* Restrict commands to one channel |
| `OPERATOR_ROLE` | Role required for start/stop/restart (default: `DCS Operator`) |

### Discord bot permissions

- **Scopes:** `bot`, `applications.commands`
- **Bot permissions:** Send Messages, Embed Links, Attach Files, Read Message History
- **Privileged intents:** Server Members (for role lookup)

## Running

```bash
python bot.py
```

The bot registers slash commands to the configured guild on startup.

## Architecture

```
bot.py                  — entry point, Bot + event handlers
config.py               — BotConfig dataclass + env loader
orchestrator_client.py  — async httpx wrapper for the orchestrator REST API
cogs/
  dcs.py                — DcsCog with all /dcs commands
```

See `docs/OpenAPI.yaml` for the full orchestrator API reference.
See `docs/tts-voice.md` for the planned voice/TTS feature.
