"""
Mission deployment helpers for node agents.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Dict

import requests

from .config import ConfigError, InstanceConfig

LOG = logging.getLogger("node_service.missions")


def deploy_mission(instance: InstanceConfig, params: Dict) -> Path:
    """
    Save a mission file for the target instance.

    Params must include:
      - filename: target file name (e.g., mission.miz)
      - One of: content_b64, download_url, source_path
      - Optional missions_dir override (defaults to instance.missions_dir)
    """
    filename = params.get("filename")
    if not filename:
        raise ConfigError("deploy_mission requires 'filename'")

    dest_dir = Path(params.get("missions_dir") or instance.missions_dir or "")
    if not dest_dir:
        raise ConfigError(
            f"No missions_dir configured for instance '{instance.cmd_key}'. "
            "Provide params.missions_dir or set instance.missions_dir in config."
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    content = _load_content(params)

    target = dest_dir / filename
    _ensure_within_directory(dest_dir, target)
    target.write_bytes(content)
    LOG.info("Mission %s saved to %s", filename, target)
    return target


def _load_content(params: Dict) -> bytes:
    if "content_b64" in params:
        try:
            return base64.b64decode(params["content_b64"])
        except Exception as exc:  # noqa: BLE001
            raise ConfigError(f"Invalid base64 payload: {exc}") from exc

    if "source_path" in params:
        path = Path(params["source_path"])
        if not path.exists():
            raise ConfigError(f"Source mission not found: {path}")
        return path.read_bytes()

    if "download_url" in params:
        url = params["download_url"]
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    raise ConfigError(
        "deploy_mission requires one of 'content_b64', 'source_path', or 'download_url'."
    )


def _ensure_within_directory(root: Path, target: Path) -> None:
    root_resolved = root.resolve()
    target_resolved = target.resolve()
    if root_resolved == target_resolved.parent:
        return
    if root_resolved not in target_resolved.parents:
        raise ConfigError(f"Refusing to write outside missions_dir: {target}")
