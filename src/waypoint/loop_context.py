"""Runtime tracking for a single resumable loop call.

``_LoopContext`` is the object the AST-rewritten function body talks to at
runtime (see ``ast_transform.py``): it validates the iterable is a concrete,
sliceable sequence, resumes from the last persisted index, and persists a
new index after each completed iteration.
"""

from pathlib import Path
from typing import Any, Iterator, Sequence, Union

from . import storage
from .exceptions import NotResumableError
from .sequence import Seq

Resumable = Union[Sequence[Any], Seq]


def _coerce_sequence(iterable: Any, loop_source: str) -> Sequence[Any]:
    if isinstance(iterable, Seq):
        return iterable.items
    if isinstance(iterable, (list, tuple, range)):
        return iterable
    raise NotResumableError(
        f"@checkpoint can't resume '{loop_source}': it iterates over a "
        f"{type(iterable).__name__}, which can't be sliced or replayed from "
        "an arbitrary index. Convert it to a list/tuple, or wrap it with "
        "waypoint.seq(...) if it has to stay lazy until decorated."
    )


class _LoopContext:
    """Tracks and persists progress for one resumable loop invocation."""

    def __init__(self, path: Path):
        self._path = path
        data = storage.read_checkpoint(path)
        self._resume_index = data["index"] if data else 0
        self._index = self._resume_index

    def track(self, iterable: Any, loop_source: str) -> Iterator[Any]:
        """Validate ``iterable`` and return an iterator resuming past
        already-completed items."""
        sequence = _coerce_sequence(iterable, loop_source)
        start = min(self._resume_index, len(sequence))
        self._index = start
        return iter(sequence[start:])

    def advance(self) -> None:
        """Record that one more iteration completed successfully."""
        self._index += 1
        storage.write_checkpoint(self._path, {"index": self._index})

    def cleanup(self) -> None:
        """Discard the checkpoint after a fully successful run."""
        storage.delete_checkpoint(self._path)
