import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


DEFAULT_CONFIG_PATH = Path(os.environ.get("HUB_CONFIG", "config/hub.json"))


class HubConfigError(Exception):
    pass


@dataclass(frozen=True)
class NodeEntry:
    token: str


@dataclass(frozen=True)
class HubConfig:
    admin_token: str
    nodes: Dict[str, NodeEntry]
    data_dir: Path

    def node_exists(self, node_id: str) -> bool:
        return node_id in self.nodes

    def get_node_token(self, node_id: str) -> str:
        entry = self.nodes.get(node_id)
        if not entry:
            raise HubConfigError(f"Unknown node '{node_id}'")
        return entry.token


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> HubConfig:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise HubConfigError(f"Hub config not found: {cfg_path}")

    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HubConfigError(f"Invalid hub config JSON: {exc}") from exc

    admin_token = raw.get("admin_token")
    nodes_raw = raw.get("nodes", {})
    data_dir = Path(raw.get("data_dir", "var"))

    if not admin_token:
        raise HubConfigError("Config missing 'admin_token'")
    if not nodes_raw:
        raise HubConfigError("Config must define at least one node entry under 'nodes'")

    nodes = {}
    for node_id, info in nodes_raw.items():
        token = info.get("token")
        if not token:
            raise HubConfigError(f"Node '{node_id}' missing 'token'")
        nodes[node_id] = NodeEntry(token=token)

    data_dir.mkdir(parents=True, exist_ok=True)

    return HubConfig(admin_token=admin_token, nodes=nodes, data_dir=data_dir)
