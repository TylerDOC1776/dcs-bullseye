"""
Orchestrator configuration — dataclasses and JSON loader.
Config path defaults to env var DCS_ORCHESTRATOR_CONFIG, then C:\\ProgramData\\DCSOrchestrator\\config.json.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(
    os.environ.get(
        "DCS_ORCHESTRATOR_CONFIG", r"C:\ProgramData\DCSOrchestrator\config.json"
    )
)


class ConfigError(Exception):
    """Raised when the orchestrator configuration cannot be loaded or validated."""


@dataclass
class OrchestratorConfig:
    api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8888
    db_path: str = r"C:\ProgramData\DCSOrchestrator\orchestrator.db"
    log_level: str = "info"
    # Public URL community hosts use to reach this orchestrator
    public_url: str = ""
    # frp tunnel settings for community hosts
    frp_server_addr: str = ""
    frp_server_port: int = 7000
    frp_token: str = ""
    frp_port_range_start: int = 8800
    frp_port_range_end: int = 8899
    registration_enabled: bool = True


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> OrchestratorConfig:
    """
    Load and validate the orchestrator configuration JSON.

    The path defaults to %ProgramData%\\DCSOrchestrator\\config.json but can be
    overridden via the DCS_ORCHESTRATOR_CONFIG environment variable or --config flag.
    """
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigError(f"Config file not found: {cfg_path}")

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid config JSON: {exc}") from exc

    return OrchestratorConfig(
        api_key=str(data.get("api_key", "")),
        host=str(data.get("host", "0.0.0.0")),
        port=int(data.get("port", 8888)),
        db_path=str(
            data.get("db_path", r"C:\ProgramData\DCSOrchestrator\orchestrator.db")
        ),
        log_level=str(data.get("log_level", "info")),
        public_url=str(data.get("public_url", "")),
        frp_server_addr=str(data.get("frp_server_addr", "")),
        frp_server_port=int(data.get("frp_server_port", 7000)),
        frp_token=str(data.get("frp_token", "")),
        frp_port_range_start=int(data.get("frp_port_range_start", 8800)),
        frp_port_range_end=int(data.get("frp_port_range_end", 8899)),
        registration_enabled=bool(data.get("registration_enabled", True)),
    )
