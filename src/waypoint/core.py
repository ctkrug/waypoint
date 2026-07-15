"""The @checkpoint decorator.

Applying @checkpoint to a function whose body is a single top-level
'for item in <sequence>:' loop makes that loop resumable: progress is
persisted to disk after each completed iteration, and a rerun with the
same arguments picks up where the last run left off instead of starting
over. See docs/VISION.md for the full design.
"""

import functools
import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, Union, cast

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


def checkpoint(
    func: Optional[F] = None,
    *,
    dir: Optional[Union[str, Path]] = None,
    key: Optional[str] = None,
) -> Any:
    """Make a function's single top-level for-loop resumable.

    Progress persists to ``.waypoint/<key>.json`` by default, keyed by the
    function and its call arguments. Killing the process mid-loop and
    rerunning with the same arguments resumes right after the last
    completed iteration. On a normal return (no exception), the checkpoint
    is deleted so the next call starts fresh.

    ``dir`` overrides the checkpoint directory (default ``.waypoint``).
    ``key`` overrides the derived checkpoint key with a fixed name, useful
    when call arguments aren't suitable for hashing (e.g. open file
    handles) or when several distinct call shapes should share one
    checkpoint namespace.
    """
    if func is None:
        return functools.partial(checkpoint, dir=dir, key=key)

    factory = build_factory(func)
    directory = Path(dir) if dir is not None else storage.DEFAULT_CHECKPOINT_DIR

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        checkpoint_key = key if key is not None else _checkpoint_key(func, args, kwargs)
        path = storage.checkpoint_path(checkpoint_key, directory)
        ctx = _LoopContext(path)
        transformed = factory(ctx)
        result = transformed(*args, **kwargs)
        ctx.cleanup()
        return result

    return cast(F, wrapper)
