"""Implementation behind ``python -m waypoint`` -- inspect and clear
on-disk checkpoints without writing ad-hoc scripts against storage.py.
"""

import json
import time
from pathlib import Path
from typing import List, TextIO

from . import storage


def _checkpoint_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


def status(directory: Path, out: TextIO) -> int:
    """Print every checkpoint under ``directory`` with its progress
    index and last-modified time. Returns a process exit code."""
    checkpoints = _checkpoint_files(directory)
    if not checkpoints:
        print(f"No checkpoints under {directory}/", file=out)
        return 0

    for path in checkpoints:
        try:
            data = storage.read_checkpoint(path)
        except json.JSONDecodeError:
            data = None
        index = data.get("index", "?") if isinstance(data, dict) else "?"
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime))
        print(f"{path.stem}\tindex={index}\t{mtime}", file=out)
    return 0


def clear(key: str, directory: Path, out: TextIO) -> int:
    """Delete the checkpoint for ``key`` under ``directory``. Returns a
    process exit code: 0 if a checkpoint was removed, 1 if none existed."""
    path = storage.checkpoint_path(key, directory)
    if not path.exists():
        print(f"No checkpoint found for key '{key}' under {directory}/", file=out)
        return 1

    storage.delete_checkpoint(path)
    print(f"Cleared checkpoint '{key}'", file=out)
    return 0
