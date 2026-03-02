import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_PATH = Path(
    os.environ.get("DCS_NODE_CONFIG", r"C:\ProgramData\DCSAdminNode\config.json")
)
DEFAULT_COMMAND_DIR = Path(
    os.environ.get("DCS_NODE_COMMAND_DIR", r"C:\ProgramData\DCSAdminNode\commands")
)
DEFAULT_LOG_BUNDLE_DIR = Path(
    os.environ.get("DCS_NODE_LOG_DIR", r"C:\ProgramData\DCSAdminNode\log_bundles")
)
VALID_ROLES = {"server", "standalone", "slave"}
VALID_TRANSPORTS = {"filesystem", "http"}


class ConfigError(Exception):
    """Raised when the node configuration cannot be loaded or validated."""


@dataclass(frozen=True)
class InstanceConfig:
    name: str
    cmd_key: str
    exe_path: str
    log_path: str
    missions_dir: Optional[str] = None


@dataclass(frozen=True)
class NodeConfig:
    node_id: str
    role: str
    vps_endpoint: str
    api_key: str
    command_transport: str = "filesystem"
    instances: List[InstanceConfig]
    heartbeat_interval: int = 30
    command_poll_interval: int = 5
    command_queue_dir: Path = DEFAULT_COMMAND_DIR
    log_bundle_dir: Path = DEFAULT_LOG_BUNDLE_DIR
    log_bundle_max_lines: int = 2000


def _parse_instances(instances: List[Dict[str, Any]]) -> List[InstanceConfig]:
    parsed: List[InstanceConfig] = []
    for item in instances:
        required = ("name", "cmd_key", "exe_path", "log_path")
        missing = [field for field in required if not item.get(field)]
        if missing:
            raise ConfigError(f"Instance {item!r} missing fields: {', '.join(missing)}")
        parsed.append(
            InstanceConfig(
                name=item["name"],
                cmd_key=item["cmd_key"].lower(),
                exe_path=item["exe_path"],
                log_path=item["log_path"],
                missions_dir=item.get("missions_dir"),
            )
        )
    return parsed


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> NodeConfig:
    """
    Load and validate the node configuration JSON.

    The path defaults to %ProgramData%\\DCSAdminNode\\config.json but can be
    overridden via the DCS_NODE_CONFIG environment variable.
    """
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigError(f"Config file not found: {cfg_path}")

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid config JSON: {exc}") from exc

    node_id = data.get("node_id")
    role = str(data.get("role", "")).lower()
    instances = data.get("instances", [])
    transport = str(data.get("command_transport", "filesystem")).lower()

    vps_endpoint = data.get("vps_endpoint")
    api_key = _resolve_api_key(data)

    if not node_id:
        raise ConfigError("Config missing 'node_id'.")
    if role not in VALID_ROLES:
        raise ConfigError(f"Config 'role' must be one of {sorted(VALID_ROLES)}.")
    if transport not in VALID_TRANSPORTS:
        raise ConfigError(f"'command_transport' must be one of {sorted(VALID_TRANSPORTS)}.")
    if transport == "http" and not vps_endpoint:
        raise ConfigError("Config must define 'vps_endpoint' when using HTTP transport.")
    if not api_key:
        raise ConfigError("API key not provided. Set 'api_key', 'api_key_file', or 'api_key_env'.")
    if not isinstance(instances, list) or not instances:
        raise ConfigError("Config must contain a non-empty 'instances' list.")

    heartbeat = int(data.get("heartbeat_interval", 30))
    poll_interval = int(data.get("command_poll_interval", 5))
    command_dir = Path(data.get("command_queue_dir", DEFAULT_COMMAND_DIR))
    log_bundle_dir = Path(data.get("log_bundle_dir", DEFAULT_LOG_BUNDLE_DIR))
    log_bundle_max_lines = int(data.get("log_bundle_max_lines", 2000))

    instance_cfgs = _parse_instances(instances)
    return NodeConfig(
        node_id=node_id,
        role=role,
        vps_endpoint=vps_endpoint or "",
        api_key=api_key,
        command_transport=transport,
        instances=instance_cfgs,
        heartbeat_interval=heartbeat,
        command_poll_interval=poll_interval,
        command_queue_dir=command_dir,
        log_bundle_dir=log_bundle_dir,
        log_bundle_max_lines=log_bundle_max_lines,
    )


def _resolve_api_key(data: Dict[str, Any]) -> Optional[str]:
    """Determine the API key from direct value, file, or environment variable."""
    key = data.get("api_key")
    if key:
        return str(key).strip()

    key_file = data.get("api_key_file")
    if key_file:
        path = Path(key_file)
        if not path.exists():
            raise ConfigError(f"api_key_file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    key_env = data.get("api_key_env")
    if key_env:
        value = os.getenv(key_env)
        if not value:
            raise ConfigError(f"Environment variable '{key_env}' not set for api_key_env.")
        return value.strip()

    return None
