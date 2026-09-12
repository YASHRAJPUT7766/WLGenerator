"""System-level helpers: disk space checks, safe path handling."""
from __future__ import annotations

import os
import shutil

from utils.errors import OutputError


def free_disk_space(path: str) -> int:
    """Return free disk space in bytes for the filesystem containing path."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        usage = shutil.disk_usage(directory)
        return usage.free
    except OSError as exc:
        raise OutputError(f"Could not determine disk space for '{directory}': {exc}")


def ensure_writable_path(path: str):
    """Raise OutputError if the path's directory doesn't exist or isn't writable."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(directory):
        raise OutputError(f"Output directory does not exist: '{directory}'")
    if not os.access(directory, os.W_OK):
        raise OutputError(f"No write permission for directory: '{directory}'")
    if os.path.exists(path) and not os.access(path, os.W_OK):
        raise OutputError(f"No write permission for existing file: '{path}'")


def check_sufficient_space(path: str, estimated_bytes: int, margin: float = 1.15):
    """Raise OutputError if free disk space is insufficient (with safety margin)."""
    needed = int(estimated_bytes * margin)
    free = free_disk_space(path)
    if free < needed:
        from utils.formatting import human_size
        raise OutputError(
            f"Insufficient disk space. Estimated need: {human_size(needed)}, "
            f"available: {human_size(free)}."
        )
