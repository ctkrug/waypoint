"""The @checkpoint decorator.

This module currently ships a pass-through placeholder. The resumable
loop engine (AST-based iterable rewriting + index persistence) lands in
Epic 1 of docs/BACKLOG.md.
"""

import functools
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


def checkpoint(func: F) -> F:
    """Mark a function's loop as resumable (placeholder implementation)."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
