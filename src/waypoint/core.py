"""The @checkpoint decorator.

Applying @checkpoint to a function whose body is a single top-level
'for item in <sequence>:' loop makes that loop resumable: progress is
persisted to disk after each completed iteration, and a rerun with the
same arguments picks up where the last run left off instead of starting
over. See docs/VISION.md for the full design.
"""

import functools
import hashlib
from typing import Any, Callable, Dict, Tuple, TypeVar, cast

from . import storage
from .ast_transform import build_factory
from .loop_context import _LoopContext

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
    """Make a function's single top-level for-loop resumable.

    Progress persists to ``.waypoint/<key>.json``, keyed by the function
    and its call arguments. Killing the process mid-loop and rerunning
    with the same arguments resumes right after the last completed
    iteration. On a normal return (no exception), the checkpoint is
    deleted so the next call starts fresh.
    """
    factory = build_factory(func)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = _checkpoint_key(func, args, kwargs)
        path = storage.checkpoint_path(key)
        ctx = _LoopContext(path)
        transformed = factory(ctx)
        result = transformed(*args, **kwargs)
        ctx.cleanup()
        return result

    return cast(F, wrapper)
