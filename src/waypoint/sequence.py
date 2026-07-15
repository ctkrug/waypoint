"""``waypoint.seq()`` -- wrap an arbitrary iterable as a resumable sequence.

``@checkpoint`` can only resume loops over a concrete, sliceable sequence
(``list``, ``tuple``, ``range``). ``seq()`` materializes any other iterable
-- a generator, a database cursor, a file handle -- into one up front so
it becomes resumable too.
"""

from typing import Any, Iterable, List


class Seq:
    """A materialized, resumable wrapper around an arbitrary iterable."""

    __slots__ = ("items",)

    def __init__(self, items: List[Any]) -> None:
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Any:
        return iter(self.items)

    def __repr__(self) -> str:
        return f"Seq({self.items!r})"


def seq(iterable: Iterable[Any]) -> Seq:
    """Materialize any iterable into a resumable ``Seq``."""
    return Seq(list(iterable))
