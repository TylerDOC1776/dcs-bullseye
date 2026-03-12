"""
argparse CLI for the DCS orchestrator.

Entry point: python -m orchestrator <command> [args]

Commands:
    serve   [--host HOST] [--port PORT]  Start the REST API server
"""

from __future__ import annotations

import argparse

from .config import ConfigError, load_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m orchestrator",
        description="DCS orchestrator — hub server managing remote DCS agent nodes.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to orchestrator config JSON (overrides DCS_ORCHESTRATOR_CONFIG env var).",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # serve
    p_serve = sub.add_parser("serve", help="Start the REST API server.")
    p_serve.add_argument(
        "--host",
        default=None,
        metavar="HOST",
        help="Bind address (overrides config; default: 0.0.0.0).",
    )
    p_serve.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORT",
        help="Listen port (overrides config; default: 8888).",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        config = load_config(args.config) if args.config else load_config()
    except ConfigError as exc:
        raise SystemExit(f"error: {exc}")

    if args.command == "serve":
        # CLI flags take precedence over config file values
        if args.host is not None:
            config.host = args.host
        if args.port is not None:
            config.port = args.port
        from .server import serve

        serve(config)
