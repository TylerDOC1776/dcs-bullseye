"""
Log collection helpers for node agents.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import ConfigError, InstanceConfig, NodeConfig

LOG = logging.getLogger("node_service.logs")


def bundle_logs(instance: InstanceConfig, config: NodeConfig, lines: Optional[int] = None) -> Path:
    log_path = Path(instance.log_path)
    if not log_path.exists():
        raise ConfigError(f"Log file not found: {log_path}")

    max_lines = lines or config.log_bundle_max_lines
    contents = _tail_lines(log_path, max_lines)

    output_dir = config.log_bundle_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{instance.cmd_key}-{timestamp}.log"
    bundle_path = output_dir / filename
    bundle_path.write_text("".join(contents), encoding="utf-8")
    LOG.info("Wrote log bundle to %s (%s lines)", bundle_path, len(contents))
    return bundle_path


def _tail_lines(path: Path, max_lines: int):
    buffer = deque(maxlen=max_lines)
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            buffer.append(line)
    return list(buffer)
