"""
Thin subprocess wrapper around nssm.exe.

All functions call nssm.exe via subprocess.run and raise NssmError on non-zero exit.
"""

from __future__ import annotations

import subprocess


class NssmError(Exception):
    """Raised when an nssm.exe call fails."""


def _run(nssm: str, *args: str) -> str:
    """Run nssm with the given arguments and return combined stdout+stderr."""
    cmd = [nssm, *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise NssmError(
            f"nssm executable not found: {nssm!r}. "
            "Install NSSM and ensure it is on PATH, or set 'nssm_path' in config."
        )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise NssmError(
            f"nssm {' '.join(args)!r} failed (exit {result.returncode}): {output}"
        )
    return output


def install(nssm: str, service: str, exe: str, args: str = "") -> None:
    """Install a new NSSM-managed service."""
    if args:
        _run(nssm, "install", service, exe, args)
    else:
        _run(nssm, "install", service, exe)


def remove(nssm: str, service: str) -> None:
    """Remove an NSSM-managed service (confirm automatically)."""
    _run(nssm, "remove", service, "confirm")


def start(nssm: str, service: str) -> None:
    """Start a service."""
    try:
        _run(nssm, "start", service)
    except NssmError as exc:
        # NSSM exits 1 with START_PENDING when the wrapped process takes a long
        # time to initialise (e.g. DCS World).  The service IS starting — treat
        # it as success and let the status poller track progress.
        if "START_PENDING" in str(exc):
            return
        raise


def stop(nssm: str, service: str) -> None:
    """Stop a service."""
    _run(nssm, "stop", service)


def restart(nssm: str, service: str) -> None:
    """Restart a service."""
    try:
        _run(nssm, "restart", service)
    except NssmError as exc:
        if "START_PENDING" in str(exc):
            return
        raise


def status(nssm: str, service: str) -> str:
    """Return the raw status string from nssm (e.g. SERVICE_RUNNING)."""
    try:
        return _run(nssm, "status", service)
    except NssmError as exc:
        # nssm status exits non-zero when the service is stopped on some versions;
        # surface the message as the status string so callers can still display it.
        return str(exc)


def set_param(nssm: str, service: str, key: str, value: str) -> None:
    """Set an NSSM service parameter."""
    _run(nssm, "set", service, key, value)
