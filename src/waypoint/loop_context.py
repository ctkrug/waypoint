"""Runtime tracking for a single resumable loop call.

``_LoopContext`` is the object the AST-rewritten function body talks to at
runtime (see ``ast_transform.py``): it validates the iterable is a concrete,
sliceable sequence, resumes from the last persisted index, and persists a
new index after each completed iteration.
"""

import json
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Sequence, Union

from . import storage
from .exceptions import NotResumableError
from .sequence import Seq

Resumable = Union[Sequence[Any], Seq]
ProgressCallback = Callable[[int, int], None]


def _load_resume_index(path: Path) -> int:
    """Read and validate the resume index from ``path``.

    A checkpoint file can be hand-edited, truncated, or written by an
    incompatible version, so its shape can't be trusted blindly: silently
    coercing a bad value (e.g. treating a negative index as "resume from
    here") could replay the wrong slice of the sequence without any sign
    something went wrong. Any of that raises a clear, actionable error
    instead -- consistent with how an unresumable loop shape fails loudly
    rather than resuming incorrectly.
    """
    try:
        data = storage.read_checkpoint(path)
    except json.JSONDecodeError as exc:
        raise NotResumableError(
            f"Checkpoint file '{path}' is not valid JSON ({exc}). It may "
            "have been hand-edited or corrupted. Delete it (or run "
            "'python -m waypoint clear <key>') to start that job fresh."
        ) from exc

    if data is None:
        return 0

    index = data.get("index") if isinstance(data, dict) else None
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise NotResumableError(
            f"Checkpoint file '{path}' has an unexpected format (expected a "
            "JSON object with a non-negative integer 'index'). It may have "
            "been hand-edited or written by an incompatible waypoint "
            "version. Delete it (or run 'python -m waypoint clear <key>') "
            "to start that job fresh."
        )
    return index


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

    def __init__(self, path: Path, on_progress: Optional[ProgressCallback] = None):
        self._path = path
        self._on_progress = on_progress
        self._total = 0
        self._resume_index = _load_resume_index(path)
        self._index = self._resume_index
        self._pending_position = self._resume_index

    def track(self, iterable: Any, loop_source: str) -> Iterator[Any]:
        """Validate ``iterable`` and return an iterator resuming past
        already-completed items."""
        sequence = _coerce_sequence(iterable, loop_source)
        start = min(self._resume_index, len(sequence))
        self._index = start
        self._pending_position = start
        self._total = len(sequence)
        return self._iter_from(sequence, start)

    def track_enumerate(self, iterable: Any, loop_source: str) -> Iterator[Any]:
        """Like :meth:`track`, but for ``for i, item in enumerate(iterable):``.

        Returns ``(index, item)`` pairs where ``index`` reflects the item's
        true position in the original sequence, even after a resume.
        """
        sequence = _coerce_sequence(iterable, loop_source)
        start = min(self._resume_index, len(sequence))
        self._index = start
        self._pending_position = start
        self._total = len(sequence)
        return self._enumerate_from(sequence, start)

    def _iter_from(self, sequence: Sequence[Any], start: int) -> Iterator[Any]:
        for position in range(start, len(sequence)):
            self._pending_position = position
            yield sequence[position]

    def _enumerate_from(self, sequence: Sequence[Any], start: int) -> Iterator[Any]:
        for position in range(start, len(sequence)):
            self._pending_position = position
            yield position, sequence[position]

    def advance(self) -> None:
        """Record that one more iteration completed successfully.

        If a `continue` skipped the appended ``advance()`` for an earlier
        item this run, ``_pending_position`` will be ahead of ``_index`` --
        persisting this later item as done would silently imply the
        skipped one completed too. In that case the checkpoint is left
        exactly where it was: the skipped item (and everything after it)
        is retried next run rather than one of them being lost forever.
        """
        if self._pending_position != self._index:
            return
        self._index += 1
        storage.write_checkpoint(self._path, {"index": self._index})
        if self._on_progress is not None:
            self._on_progress(self._index, self._total)

    def cleanup(self) -> None:
        """Discard the checkpoint after a fully successful run."""
        storage.delete_checkpoint(self._path)
