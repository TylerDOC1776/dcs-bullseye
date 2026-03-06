from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    pass


@dataclass
class BotConfig:
    discord_token: str
    guild_id: int
    orchestrator_url: str
    orchestrator_api_key: str
    bot_channel_id: int | None = None
    operator_role: str = "DCS Operator"
    admin_role: str = "DCS Admin"
    events_channel_id: int | None = None  # SSE notifications; falls back to bot_channel_id
    status_channel_id: int | None = None  # pinned live-status embed
    external_servers: list[dict] = field(default_factory=list)  # [{name, ip, port}]
    installer_base_url: str = ""  # public URL used in /dcs invite one-liner; defaults to orchestrator_url
    agent_zip_sha256: str = ""   # SHA-256 of agent.zip served at /install/agent.zip; included in invite command
    auto_restart_exclude: list[str] = field(default_factory=list)  # instance names exempt from keepalive auto-start


def load_config() -> BotConfig:
    token = os.getenv("DISCORD_TOKEN")
    guild_raw = os.getenv("GUILD_ID")
    orch_url = os.getenv("ORCHESTRATOR_URL")

    missing = [name for name, val in [
        ("DISCORD_TOKEN", token),
        ("GUILD_ID", guild_raw),
        ("ORCHESTRATOR_URL", orch_url),
    ] if not val]
    if missing:
        raise ConfigError(f"Missing required env vars: {', '.join(missing)}")

    def _opt_int(key: str) -> int | None:
        raw = os.getenv(key, "").strip()
        return int(raw) if raw else None

    return BotConfig(
        discord_token=token,  # type: ignore[arg-type]
        guild_id=int(guild_raw),  # type: ignore[arg-type]
        orchestrator_url=orch_url.rstrip("/"),  # type: ignore[arg-type]
        orchestrator_api_key=os.getenv("ORCHESTRATOR_API_KEY", ""),
        bot_channel_id=_opt_int("BOT_CHANNEL_ID"),
        operator_role=os.getenv("OPERATOR_ROLE", "DCS Operator"),
        admin_role=os.getenv("ADMIN_ROLE", "DCS Admin"),
        events_channel_id=_opt_int("EVENTS_CHANNEL_ID"),
        status_channel_id=_opt_int("STATUS_CHANNEL_ID"),
        external_servers=json.loads(os.getenv("EXTERNAL_SERVERS", "[]")),
        installer_base_url=os.getenv("INSTALLER_BASE_URL", orch_url).rstrip("/"),  # type: ignore[arg-type]
        agent_zip_sha256=os.getenv("AGENT_ZIP_SHA256", ""),
        auto_restart_exclude=[n.strip() for n in os.getenv("AUTO_RESTART_EXCLUDE", "").split(",") if n.strip()],
    )
