"""
Node-side control helpers for DCS server instances.

This module replaces the legacy restart EXE with pure Python routines that can
be imported by the Windows service or executed directly from the CLI.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

import psutil
import subprocess

from .config import ConfigError, NodeConfig, load_config
from .logs import bundle_logs
from .missions import deploy_mission

LOG = logging.getLogger("node_service.controller")
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)


class DcsController:
    """High-level operations for a single node."""

    def __init__(self, config: NodeConfig):
        self.config = config
        self.instances = {inst.cmd_key: inst for inst in config.instances}

    def _get_instance(self, key: str):
        instance = self.instances.get(key.lower())
        if not instance:
            raise ConfigError(f"Unknown instance key '{key}'. Known: {list(self.instances)}")
        return instance

    def start_instance(self, key: str) -> None:
        instance = self._get_instance(key)
        exe_path = Path(instance.exe_path)
        if not exe_path.exists():
            raise FileNotFoundError(f"Executable not found: {exe_path}")

        cmd = [str(exe_path), "-w", instance.name]
        LOG.info("Starting instance %s with command %s", instance.name, cmd)
        subprocess.Popen(cmd, creationflags=DETACHED_PROCESS)  # noqa: S603,S607

    def stop_instance(self, key: str, timeout: int = 30) -> None:
        instance = self._get_instance(key)
        LOG.info("Stopping instance %s", instance.name)

        processes = self._matching_processes(instance.name)
        for proc in processes:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                LOG.warning("Force killing PID %s for %s", proc.pid, instance.name)
                proc.kill()

    def restart_instance(self, key: str) -> None:
        self.stop_instance(key)
        time.sleep(5)
        self.start_instance(key)

    def deploy_mission(self, key: str, params: dict) -> Path:
        instance = self._get_instance(key)
        return deploy_mission(instance, params or {})

    def collect_logs(self, key: str, lines: Optional[int] = None) -> Path:
        instance = self._get_instance(key)
        return bundle_logs(instance, self.config, lines=lines)

    def instance_statuses(self) -> List[dict]:
        statuses: List[dict] = []
        for instance in self.instances.values():
            processes = self._matching_processes(instance.name)
            statuses.append(
                {
                    "cmd_key": instance.cmd_key,
                    "name": instance.name,
                    "running": bool(processes),
                    "pids": [proc.pid for proc in processes],
                }
            )
        return statuses

    def _matching_processes(self, instance_name: str) -> List[psutil.Process]:
        matches: List[psutil.Process] = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            if proc.info["name"] != "DCS_server.exe":
                continue
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if f"-w {instance_name}" in cmdline:
                matches.append(proc)
        return matches


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control DCS instances via Python.")
    parser.add_argument("action", choices=["start", "stop", "restart"], help="Operation to perform")
    parser.add_argument("instance", help="Instance cmd_key defined in config")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.json (defaults to %%ProgramData%%\\DCSAdminNode)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    cfg = load_config(args.config) if args.config else load_config()
    controller = DcsController(cfg)

    try:
        if args.action == "start":
            controller.start_instance(args.instance)
        elif args.action == "stop":
            controller.stop_instance(args.instance)
        else:
            controller.restart_instance(args.instance)
    except Exception as exc:  # pylint: disable=broad-except
        LOG.error("Failed to %s %s: %s", args.action, args.instance, exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
