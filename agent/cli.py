"""
argparse CLI for the DCS agent.

Entry point: python -m agent <command> [args]

Commands:
    status  [<name> | --all]       Show service status (default: all)
    start   <name> | --all         Start service(s)
    stop    <name> | --all         Stop service(s)
    restart <name> | --all         Restart service(s)
    install <name> | --all         Install as NSSM service(s)
    remove  <name> | --all         Remove NSSM service(s)
    logs    <name> [--lines N]     Tail DCS log (default 50 lines)
    serve   [--host HOST] [--port PORT]  Start the REST API server
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from .config import AgentConfig, ConfigError, InstanceConfig, load_config
from .controller import DcsController


# ---------------------------------------------------------------------------
# Instance resolution
# ---------------------------------------------------------------------------

def _find_instance(config: AgentConfig, name: str) -> InstanceConfig:
    """Look up an instance by name or service_name (case-insensitive)."""
    key = name.lower()
    for inst in config.instances:
        if inst.name.lower() == key or inst.service_name.lower() == key:
            return inst
    names = ", ".join(f"{i.name!r}/{i.service_name!r}" for i in config.instances)
    raise SystemExit(f"error: no instance matching {name!r}. Known: {names}")


def _resolve_instances(config: AgentConfig, name: str | None, all_flag: bool) -> list[InstanceConfig]:
    if all_flag:
        return config.instances
    if name:
        return [_find_instance(config, name)]
    raise SystemExit("error: specify an instance name or --all")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_status(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    if args.name or args.all:
        instances = _resolve_instances(config, args.name, args.all)
        rows = []
        for inst in instances:
            from .nssm import NssmError
            try:
                svc_status = ctrl.status(inst)
            except NssmError as exc:
                svc_status = f"ERROR: {exc}"
            rows.append((inst.name, inst.service_name, svc_status))
    else:
        # default: all
        statuses = ctrl.all_statuses()
        rows = [(s["name"], s["service"], s["status"]) for s in statuses]

    _print_table(rows)


def _cmd_start(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    for inst in _resolve_instances(config, args.name, args.all):
        print(f"Starting {inst.name} ({inst.service_name})...")
        ctrl.start(inst)
        print(f"  OK")


def _cmd_stop(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    for inst in _resolve_instances(config, args.name, args.all):
        print(f"Stopping {inst.name} ({inst.service_name})...")
        ctrl.stop(inst)
        print(f"  OK")


def _cmd_restart(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    for inst in _resolve_instances(config, args.name, args.all):
        print(f"Restarting {inst.name} ({inst.service_name})...")
        ctrl.restart(inst)
        print(f"  OK")


def _cmd_install(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    for inst in _resolve_instances(config, args.name, args.all):
        print(f"Installing {inst.name} ({inst.service_name})...")
        ctrl.install(inst)
        print(f"  OK")


def _cmd_remove(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    for inst in _resolve_instances(config, args.name, args.all):
        print(f"Removing {inst.name} ({inst.service_name})...")
        ctrl.remove(inst)
        print(f"  OK")


def _cmd_serve(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    from .server import serve
    # CLI flags take precedence over config file values
    if args.host is not None:
        config.host = args.host
    if args.port is not None:
        config.port = args.port
    serve(config)


def _cmd_logs(ctrl: DcsController, config: AgentConfig, args: argparse.Namespace) -> None:
    inst = _find_instance(config, args.name)
    try:
        lines = ctrl.tail_logs(inst, lines=args.lines)
    except FileNotFoundError as exc:
        raise SystemExit(f"error: {exc}")
    print(f"--- Last {args.lines} lines of {inst.log_path} ---")
    for line in lines:
        print(line, end="")


# ---------------------------------------------------------------------------
# Table formatting
# ---------------------------------------------------------------------------

def _print_table(rows: list[tuple[str, str, str]]) -> None:
    headers = ("Name", "Service", "Status")
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "  ".join("-" * w for w in col_widths)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*row))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent",
        description="DCS agent — manage DCS World server instances as Windows services via NSSM.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to agent config JSON (overrides DCS_AGENT_CONFIG env var).",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # Helper to add name/--all to a subparser
    def _add_target(p: argparse.ArgumentParser, name_required: bool = False) -> None:
        group = p.add_mutually_exclusive_group(required=name_required)
        group.add_argument("name", nargs="?", default=None, metavar="<name>",
                           help="Instance name or service name.")
        group.add_argument("--all", action="store_true", help="Apply to all instances.")

    # status
    p_status = sub.add_parser("status", help="Show service status.")
    _add_target(p_status, name_required=False)

    # start
    p_start = sub.add_parser("start", help="Start service(s).")
    _add_target(p_start, name_required=True)

    # stop
    p_stop = sub.add_parser("stop", help="Stop service(s).")
    _add_target(p_stop, name_required=True)

    # restart
    p_restart = sub.add_parser("restart", help="Restart service(s).")
    _add_target(p_restart, name_required=True)

    # install
    p_install = sub.add_parser("install", help="Install instance(s) as NSSM services.")
    _add_target(p_install, name_required=True)

    # remove
    p_remove = sub.add_parser("remove", help="Remove NSSM service(s).")
    _add_target(p_remove, name_required=True)

    # logs
    p_logs = sub.add_parser("logs", help="Tail DCS log for an instance.")
    p_logs.add_argument("name", metavar="<name>", help="Instance name or service name.")
    p_logs.add_argument("--lines", type=int, default=50, metavar="N",
                        help="Number of lines to show (default: 50).")

    # serve
    p_serve = sub.add_parser("serve", help="Start the REST API server.")
    p_serve.add_argument("--host", default=None, metavar="HOST",
                         help="Bind address (overrides config; default: 0.0.0.0).")
    p_serve.add_argument("--port", type=int, default=None, metavar="PORT",
                         help="Listen port (overrides config; default: 8787).")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_HANDLERS: dict[str, Callable] = {
    "status": _cmd_status,
    "start": _cmd_start,
    "stop": _cmd_stop,
    "restart": _cmd_restart,
    "install": _cmd_install,
    "remove": _cmd_remove,
    "logs": _cmd_logs,
    "serve": _cmd_serve,
}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        config = load_config(args.config) if args.config else load_config()
    except ConfigError as exc:
        raise SystemExit(f"error: {exc}")

    ctrl = DcsController(config)

    handler = _HANDLERS[args.command]
    try:
        handler(ctrl, config, args)
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"error: {exc}")
