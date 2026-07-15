"""The @checkpoint decorator.

This module currently ships the checkpoint-key derivation used to keep
per-call progress isolated. The resumable loop engine (AST-based iterable
rewriting + index persistence) lands next in Epic 1 of docs/BACKLOG.md.
"""

import functools
import hashlib
from typing import Any, Callable, Dict, Tuple, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def _checkpoint_key(func: Callable[..., Any], args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
    """Derive a stable checkpoint key from function identity and call args.

    Two calls to the same function with equal arguments produce the same
    key (so an interrupted run resumes); calls with different arguments
    produce different keys (so they never share progress).
    """
    qualname = f"{func.__module__}.{func.__qualname__}"
    payload = repr((args, tuple(sorted(kwargs.items()))))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{qualname}-{digest}"


def checkpoint(func: F) -> F:
    """Mark a function's loop as resumable (placeholder implementation)."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return cast(F, wrapper)
