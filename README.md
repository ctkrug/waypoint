# waypoint

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

## Why

Long-running scripts get killed: Ctrl-C, an OOM, a preempted spot
instance, a laptop going to sleep. The usual fix is boilerplate —
manually track an index, write it to a file, load it back on the next
run, wrap the loop body in `try`/`except`. It's easy to get wrong and
it clutters the actual logic.

`waypoint` does this for you. Decorate the function, keep writing
plain Python.

## How it works (v1 design)

- The decorated function's loop must iterate over a concrete,
  indexable sequence — a `list`, `tuple`, `range`, or anything wrapped
  in `waypoint.seq(...)`. (Plain generators can't be resumed without
  re-running them, so `waypoint` raises a clear error instead of
  guessing.)
- Progress is persisted to a small JSON file under `.waypoint/`,
  keyed by the function and its call arguments, written atomically so
  a hard kill never corrupts it.
- On a fresh call, `waypoint` checks for an existing checkpoint for
  that exact call and, if found, transparently resumes from the
  recorded index.
- On successful completion, the checkpoint is deleted — the next run
  starts clean.

See [`docs/VISION.md`](docs/VISION.md) for the full design and
[`docs/BACKLOG.md`](docs/BACKLOG.md) for what's built vs. planned.

## Status

Early scaffold — the decorator above is the target API; the resumable
engine itself is being built (see the backlog). Not yet on PyPI.

## Install (once published)

    pip install waypoint

## Development

    pip install -e ".[dev]"
    pytest

## License

MIT — see [LICENSE](LICENSE).
