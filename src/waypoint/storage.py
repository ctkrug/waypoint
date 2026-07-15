"""Disk-backed checkpoint storage.

v1 will persist per-call progress under ``.waypoint/<key>.json`` using
atomic write-then-replace so a killed process never leaves a corrupt
checkpoint (see docs/BACKLOG.md, Epic 1).
"""

from pathlib import Path

DEFAULT_CHECKPOINT_DIR = Path(".waypoint")


def checkpoint_path(key: str, directory: Path = DEFAULT_CHECKPOINT_DIR) -> Path:
    """Return the on-disk path for a given checkpoint key."""
    return directory / f"{key}.json"
