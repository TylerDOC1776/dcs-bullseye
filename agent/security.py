"""
Input validation helpers for file operations.
"""

from __future__ import annotations

from pathlib import Path


def sanitize_miz_filename(name: str) -> str:
    """
    Validate and return a safe .miz filename.

    Raises ValueError if the name contains path separators, traversal sequences,
    is not a .miz file, or exceeds reasonable length limits.
    """
    if not name or len(name) > 255:
        raise ValueError("Invalid filename")
    if name != Path(name).name:
        raise ValueError("Path separators are not allowed in filenames")
    if ".." in name:
        raise ValueError("Path traversal sequences are not allowed")
    if not name.lower().endswith(".miz"):
        raise ValueError("Only .miz files are accepted")
    return name


def safe_join(root: Path, filename: str) -> Path:
    """
    Join root and filename, then verify the result stays inside root.

    Raises ValueError if the resolved path escapes the root directory.
    """
    target = (root / filename).resolve()
    root_resolved = root.resolve()
    if not str(target).startswith(str(root_resolved) + "/") and target != root_resolved / filename:
        # Use os.path.commonpath for cross-platform correctness
        import os
        if os.path.commonpath([str(target), str(root_resolved)]) != str(root_resolved):
            raise ValueError(f"Resolved path escapes root directory: {target}")
    return target
