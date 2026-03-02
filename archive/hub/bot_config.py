import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    discord_token: str
    hub_url: str
    hub_token: str
    default_node: Optional[str]
    command_channel_id: Optional[int]


def load_bot_config() -> BotConfig:
    load_dotenv()
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    hub_url = os.getenv("HUB_BASE_URL")
    hub_token = os.getenv("HUB_ADMIN_TOKEN")
    default_node = os.getenv("HUB_DEFAULT_NODE")
    command_channel_id = os.getenv("COMMAND_CHANNEL_ID")

    if not discord_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required.")
    if not hub_url:
        raise RuntimeError("HUB_BASE_URL is required.")
    if not hub_token:
        raise RuntimeError("HUB_ADMIN_TOKEN is required.")

    channel_id = int(command_channel_id) if command_channel_id else None

    return BotConfig(
        discord_token=discord_token,
        hub_url=hub_url,
        hub_token=hub_token,
        default_node=default_node,
        command_channel_id=channel_id,
    )
