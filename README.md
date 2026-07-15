# waypoint

[![CI](https://github.com/ctkrug/waypoint/actions/workflows/ci.yml/badge.svg)](https://github.com/ctkrug/waypoint/actions/workflows/ci.yml)

One decorator that makes any Python loop resumable. Kill the process
mid-run, rerun the script, and it picks up exactly where it left off.

```python
from waypoint import checkpoint

@checkpoint
def process_all(items):
    for item in items:
        do_something_slow(item)
```

Hit Ctrl-C at item 4,000 of 10,000. Rerun the script. `waypoint` skips
the 4,000 already-processed items and resumes at 4,001 — no manual
save/restore code, no external job queue, no config.

### Try it yourself

```
git clone https://github.com/ctkrug/waypoint.git
cd waypoint
pip install -e .
python examples/slow_loop.py
# hit Ctrl-C partway through...
python examples/slow_loop.py
# ...and it resumes right after the last completed item.
```

## Why

Long-running scripts get killed: Ctrl-C, an OOM, a preempted spot
instance, a laptop going to sleep. The usual fix is boilerplate —
manually track an index, write it to a file, load it back on the next
run, wrap the loop body in `try`/`except`. It's easy to get wrong and
it clutters the actual logic.

`waypoint` does this for you. Decorate the function, keep writing
plain Python.

## How it works

- `@checkpoint` parses the decorated function's source once, finds its
  single top-level `for item in <sequence>:` loop, and rewrites the
  iterated expression to resume from a persisted index — the loop
  body itself is untouched.
- The loop must iterate over a concrete, sliceable sequence — a
  `list`, `tuple`, `range`, or anything wrapped in `waypoint.seq(...)`.
  Plain generators can't be resumed without re-running them from
  scratch, so decorating a loop over one raises `NotResumableError`
  with an actionable message instead of silently doing the wrong
  thing.
- Progress is persisted to a small JSON file under `.waypoint/` (atomic
  write-then-replace, so a hard kill never corrupts it), keyed by the
  function's qualified name plus a hash of its call arguments — calling
  the same function with different arguments never shares progress.
  That write includes an `fsync` on every iteration, trading some
  per-item overhead for durability — fine for loop bodies doing real
  work (API calls, file I/O), but if your body is sub-millisecond
  pure-Python, the checkpoint write will dominate. Batch such loops
  into chunks before decorating if that matters.
- The index only advances after an iteration *completes*. If the loop
  body raises partway through an item, that item is retried on the
  next run rather than skipped — `waypoint` guarantees you never redo
  completed work, not that side effects run exactly once. Make loop
  bodies idempotent if that matters for your use case.
- On successful completion (loop exhausted, function returns without
  raising), the checkpoint is deleted — the next run starts clean.

### Resuming a non-list iterable

```python
from waypoint import checkpoint, seq

@checkpoint
def process_all(items):
    for item in items:
        do_something_slow(item)

process_all(seq(fetch_records_from_api()))  # materializes once, then resumes
```

### Configuration

```python
@checkpoint(dir=".state", key="job-42")
def process_all(items):
    ...
```

`dir` overrides where checkpoints are written (default `.waypoint/`).
`key` overrides the derived checkpoint key with a fixed name — useful
when call arguments aren't hashable/reprable in a stable way, or when
you want several differently-shaped calls to share one checkpoint.

### Progress reporting

```python
@checkpoint(on_progress=lambda index, total: print(f"{index}/{total}"))
def process_all(items):
    for item in items:
        do_something_slow(item)
```

`on_progress(index, total)` fires after each iteration that advances
the checkpoint. Omitting it costs nothing extra. Note this is tied to
checkpoint progress, not just "the loop body ran": an item skipped past
by `continue` after an earlier `continue` in the same run won't fire
`on_progress` either, for the same reason it isn't checkpointed (see
"Known v1 limitations" below).

### CLI

```
python -m waypoint status            # list stored checkpoints
python -m waypoint status --dir X    # ... under a non-default directory
python -m waypoint clear <key>       # delete one checkpoint, e.g. to force a fresh run
```

### Known v1 limitations

- Only the function's first top-level `for` loop is made resumable;
  loops nested inside `if`/`try`/`with`, or a second loop later in the
  function, are left alone.
- The loop target must be a single name (`for item in ...:`) or an
  `enumerate(...)` pair (`for i, item in enumerate(...):`) — other
  unpacking targets aren't supported.
- A loop body that `continue`s past the tracked item won't advance the
  checkpoint for that item, so it's retried on the next run. Because
  progress is one linear index, the checkpoint also can't record any
  *later* item in that same run as done without falsely implying the
  skipped one finished too — so it doesn't: everything after the first
  `continue` in a run is simply retried again next time, alongside the
  skipped item itself. Nothing is ever silently dropped, but a
  `continue`-heavy loop pays for that safety in redone work.
- The decorated function needs real source available (`inspect.getsource`)
  — functions defined dynamically via `exec`/the REPL aren't supported.
- Two calls to the same checkpointed function with the same effective
  arguments must not run concurrently (multiple threads, or multiple
  processes) — there's no cross-call locking, so they'd race on the same
  checkpoint file. One process, one call per checkpoint key at a time.
- The checkpoint key hashes `repr()` of the call arguments. That's
  stable for plain data (lists, tuples, strings, numbers), but a `set`
  or `frozenset` argument containing strings can repr in a different
  order on every process run (Python's hash randomization), producing a
  different key each time and silently defeating resume. Calling with
  an implicit default (`f(items)`) vs. the same value passed explicitly
  (`f(items, batch_size=10)`) also hashes differently, for the same
  reason. Pass `key=` explicitly if your arguments hit either case.

See [`docs/VISION.md`](docs/VISION.md) for the full design and
[`docs/BACKLOG.md`](docs/BACKLOG.md) for what's built vs. planned.

## Status

The core resumable-loop engine is implemented and tested end-to-end.
Not yet on PyPI.

## Install (once published)

    pip install waypoint

## Development

    pip install -e ".[dev]"
    pytest

## License

MIT — see [LICENSE](LICENSE).
