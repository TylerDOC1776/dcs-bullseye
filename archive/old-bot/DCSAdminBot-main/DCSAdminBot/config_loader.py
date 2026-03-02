import os
import json
from dotenv import load_dotenv

def load_config():
    load_dotenv()

    with open("config/servers.json") as f:
        servers = json.load(f)["instances"]

    sample_log_path = next(iter(servers.values()))["log"]
    base_path = os.path.abspath(os.path.join(sample_log_path, "..", "..", ".."))

    return {
        "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN"),
        "ERROR_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL"),
        "COMMAND_CHANNEL_ID": int(os.getenv("COMMAND_CHANNEL_ID")),
        "SERVERS": servers,
        "DCS_SAVED_GAMES": base_path,
        "DCS_ACTIVE_MISSIONS": os.path.join(base_path, "Active Missions")
    }
