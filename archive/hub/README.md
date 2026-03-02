# Hub API (VPS)

This service runs on the Ubuntu VPS and exposes HTTPS endpoints for Windows nodes to fetch commands and acknowledge results. It also provides an admin API for enqueueing actions such as `restart`, `deploy_mission`, or `collect_logs`.

## Configuration

Create `config/hub.json` (or set `HUB_CONFIG` to another path):

```json
{
  "admin_token": "ADMIN_SECRET",
  "data_dir": "var",
  "nodes": {
    "southern-01": { "token": "NODE_TOKEN_SOUTHERN" },
    "bravo-02": { "token": "NODE_TOKEN_BRAVO" }
  }
}
```

## Running the API

```bash
pip install -r requirements.txt
python -m hub.server
# or
uvicorn hub.api:create_app --factory
```

The default server listens on port `8080`. Adjust via uvicorn arguments or wrap with systemd + nginx for TLS.

## Endpoints

- `POST /api/commands` — Admin-only. Body:
  ```json
  {
    "node_id": "southern-01",
    "action": "deploy_mission",
    "instance": "southern",
    "params": {
      "filename": "OpOverlord.miz",
      "content_b64": "<base64>"
    }
  }
  ```
  Returns the queued command.
- `GET /api/commands?node_id=southern-01` — Admin-only list for auditing.
- `GET /api/nodes/{node_id}/commands` — Node poll endpoint. Requires header `Authorization: Bearer <node_token>`.
- `POST /api/nodes/{node_id}/commands/{command_id}/ack` — Node acknowledges completion:
  ```json
  { "success": true, "message": "Mission stored at C:/..." }
  ```
- `POST /api/nodes/{node_id}/heartbeat` — Node telemetry payload (status, per-instance running states, optional version). Requires node token.
- `GET /api/heartbeats` — Admin-only list of the most recent heartbeat per node.

## Queue Flow

1. Admin enqueues command via REST (or future Discord bot integration).
2. Node service polls `/api/nodes/<id>/commands` (using `HttpCommandClient`).
3. Node executes the action and POSTs to `/ack` with success + message. The hub stores audit data in `var/commands.json` and removes the command from pending lists.
4. Nodes using HTTP transport additionally post `/heartbeat` so the hub/Discord bot can surface node health.

## Log Uploads

- Nodes issue `collect_logs` commands like before, but when they're configured for HTTP transport they POST the resulting bundle to `/api/nodes/{node}/logs`. The hub saves metadata in `logs.json` and the file under `data_dir/log_files/`.
- Admins (or the Discord bot) can call `GET /api/logs` to list bundles and `GET /api/logs/{log_id}` to download the text attachment for posting back to Discord.

## Next Steps

- Integrate Discord bot to call `POST /api/commands`.
- Add WebSocket push notifications to reduce polling overhead.
- Persist logs in a database (SQLite/Postgres) for richer reporting.

## Discord Bot Integration

`src/hub/bot.py` provides a discord.py bot that enqueues commands via the admin API.

Environment variables:

- `DISCORD_BOT_TOKEN`
- `HUB_BASE_URL` (e.g., `https://hub.example.com`)
- `HUB_ADMIN_TOKEN`
- `HUB_DEFAULT_NODE` *(optional)* — fallback node ID when `!commands` doesn’t include one.
- `COMMAND_CHANNEL_ID` *(optional)* — restrict commands to a single channel.

Run with:

```bash
python -m hub.bot
```

Commands:

- `!start <node> <instance>`
- `!stop <node> <instance>`
- `!restart <node> <instance>`
- `!deploy <node> <instance>` (attach `.miz`)
- `!logs <node> <instance> [lines]` — queues a bundle and auto-posts it when ready.
- `!logfiles [node]` — lists the latest uploaded bundles.
- `!logfile <log_id>` — downloads a specific bundle.
- `!commands [node]`
