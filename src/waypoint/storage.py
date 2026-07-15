"""Disk-backed checkpoint storage.

Checkpoints persist per-call progress under ``.waypoint/<key>.json``. Writes
are temp-file-then-``os.replace``, so a reader never observes a half-written
file even if the process is killed mid-write.
"""

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CHECKPOINT_DIR = Path(".waypoint")


def checkpoint_path(key: str, directory: Path = DEFAULT_CHECKPOINT_DIR) -> Path:
    """Return the on-disk path for a given checkpoint key."""
    return directory / f"{key}.json"


def read_checkpoint(path: Path) -> Optional[Dict[str, Any]]:
    """Return the checkpoint's stored data, or ``None`` if it doesn't exist."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
            return data
    except FileNotFoundError:
        return None


def write_checkpoint(path: Path, data: Dict[str, Any]) -> None:
    """Atomically persist ``data`` to ``path``.

    Writes to a temp file in the same directory and ``os.replace``s it into
    place, so a hard kill mid-write leaves either the old file or the new
    one -- never a truncated/corrupt one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp_name)
        raise


def delete_checkpoint(path: Path) -> None:
    """Remove a checkpoint file if it exists; a no-op otherwise."""
    path.unlink(missing_ok=True)
