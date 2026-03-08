"""
Input validation helpers for file operations.
"""

from __future__ import annotations

import re
from pathlib import Path

# Allowlist: alphanumeric start, then alphanumeric/spaces/dots/underscores/hyphens, .miz extension.
# Covers typical DCS mission names; rejects all path separators and traversal sequences.
_SAFE_MIZ_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]*\.miz$", re.IGNORECASE)


def sanitize_miz_filename(name: str) -> str:
    """
    Validate and return a safe .miz filename.

    Raises ValueError if the name contains path separators, traversal sequences,
    invalid characters, is not a .miz file, or exceeds reasonable length limits.
    """
    if not name or len(name) > 255:
        raise ValueError("Invalid filename")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*\.miz", name, re.IGNORECASE):
        raise ValueError("Filename contains invalid characters or is not a .miz file")
    return name


def safe_join(root: Path, filename: str) -> Path:
    """
    Join root and filename, then verify the result stays inside root.

    Raises ValueError if the resolved path escapes the root directory.
    """
    root_resolved = root.resolve()
    target = (root_resolved / filename).resolve()
    if not target.is_relative_to(root_resolved):
        raise ValueError(f"Resolved path escapes root directory: {target}")
    return target
