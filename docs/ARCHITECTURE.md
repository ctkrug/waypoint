# Architecture

A map of the codebase for anyone (human or otherwise) picking this up
cold. See [`docs/VISION.md`](VISION.md) for *why* it's built this way
and [`docs/BACKLOG.md`](BACKLOG.md) for what's done vs. planned.

## Package layout

```
src/waypoint/
  __init__.py       # public API: checkpoint, seq, Seq, NotResumableError
  core.py            # the @checkpoint decorator itself
  ast_transform.py    # parses + rewrites the decorated function's loop
  loop_context.py     # runtime object the rewritten loop talks to
  storage.py           # atomic on-disk checkpoint read/write/delete
  sequence.py           # Seq / seq() -- wraps arbitrary iterables
  exceptions.py          # NotResumableError
  __main__.py             # `python -m waypoint` CLI (not yet implemented)
```

## How a decorated call flows

1. **Decoration time** (`core.checkpoint`): `ast_transform.build_factory(func)`
   parses `func`'s source with `ast.parse`, finds its single top-level
   `for item in <sequence>:` statement, and rewrites the loop in place:
   - `stmt.iter` becomes `__waypoint_ctx__.track(<original iter expr>, "<loop source>")`
   - a `__waypoint_ctx__.advance()` call is appended as the loop body's
     last statement.

   If no top-level `for` loop exists, or its target isn't a single name
   (e.g. `for i, item in enumerate(...)`), this raises `NotResumableError`
   immediately — a decoration-time, not call-time, failure.

   The rewritten `FunctionDef` is nested inside a synthetic
   `__waypoint_factory__(ctx, *freevars)` function and `compile()`d once.
   `freevars` mirrors `func.__code__.co_freevars` so that if the original
   function closes over a variable from its enclosing scope (a helper
   function, a shared client), that still works after recompilation —
   `build_factory` returns a `make(ctx)` closure that re-reads the
   original closure cells (`func.__closure__[i].cell_contents`) on every
   call and passes them into the factory, which lets Python's own
   compiler wire up fresh closure cells for the nested function.

2. **Call time** (`core.checkpoint.wrapper`): each call computes a
   checkpoint key (`core._checkpoint_key`: `module.qualname` + a sha256
   hash of `repr((args, sorted(kwargs.items())))`, unless an explicit
   `key=` was passed to the decorator), builds a `loop_context._LoopContext`
   bound to `.waypoint/<key>.json` (or a custom `dir=`), and calls the
   transformed function through it.

3. **Inside the loop** (`loop_context._LoopContext`):
   - `track(iterable, loop_source)` validates the iterable is a
     `list`/`tuple`/`range`/`Seq` (raising `NotResumableError` naming the
     loop otherwise), slices it from the last persisted index, and
     returns an iterator over the remainder.
   - `advance()` runs after each iteration's body completes — not on
     exception, not on `continue` — persisting `{"index": n}` via
     `storage.write_checkpoint` (temp file + `os.replace`, so a hard kill
     mid-write never corrupts the checkpoint).
   - If the call returns normally, `wrapper` calls `ctx.cleanup()`,
     deleting the checkpoint file so the next call starts fresh.

This is why a killed run's in-flight item gets *retried* on rerun rather
than skipped: `advance()` only ever moves the index past an iteration
that fully completed.

## Known v1 constraints (by design, not oversight)

- One resumable loop per function: only the first top-level `for` is
  rewritten.
- Loop target must be a single name, not a tuple unpack (`enumerate()`
  support is Epic 3.1, not yet built).
- `continue` inside the loop body skips the appended `advance()` call
  too, so that item is retried on the next run.
- The decorated function must have real, `inspect.getsource`-readable
  source (a file on disk, not `exec`/REPL-defined).
- Mutating a rebound (`nonlocal`) closure variable inside the loop body
  doesn't propagate back to the caller's scope, since a fresh cell is
  created on each call.

## Running it

```
pip install -e ".[dev]"
pytest                        # full suite
ruff check src tests           # lint
mypy src                        # types
```

`examples/slow_loop.py` is a runnable demo of the wow moment: run it,
Ctrl-C partway through, rerun, and it resumes.
