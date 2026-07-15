# Vision

## The problem

Long-running Python scripts get killed: Ctrl-C, an OOM, a preempted
spot instance, a laptop going to sleep, a flaky API that finally times
out on item 8,000 of 10,000. Restarting means redoing all completed
work — wasted time, wasted API calls, wasted money.

The usual fix is boilerplate: track an index by hand, write it to a
file after each iteration, load it back at the top of the script,
wrap the loop body in `try`/`except` to make sure the write actually
happens. It's easy to get subtly wrong (off-by-one on resume, a
half-written state file, forgetting to clear it on success) and it
clutters the one thing the script was supposed to do.

## Who it's for

Anyone writing a one-off or semi-regular Python script that iterates
over a large collection and might not finish in one sitting:

- data engineers backfilling or transforming a large dataset
- people scraping or calling a rate-limited/paid API over many records
- ML practitioners running long preprocessing or evaluation loops
- anyone on a laptop that might sleep, lose power, or get Ctrl-C'd

## The core idea

One decorator: `@waypoint.checkpoint`. Apply it to a function whose
body is a loop over a concrete sequence. That's the whole API surface
for the common case:

```python
from waypoint import checkpoint

@checkpoint
def process_all(items):
    for item in items:
        do_something_slow(item)
```

Kill the process at item 4,000 of 10,000. Rerun the script exactly as
before. `waypoint` resumes at item 4,001 — no manual save/restore
code, no external job queue, no config.

## Key design decisions

- **AST-based transparency.** Rather than asking users to rewrite
  `for item in items` as `for item in waypoint.resume(items)`,
  `waypoint` parses the decorated function's source once (cached) and
  rewrites the iterated expression to slice from the saved resume
  index. The loop body itself is untouched — the mechanism stays out
  of the way of the logic.

- **Determinism is required, and the requirement is explicit.**
  v1 only resumes loops over a concrete sequence: `list`, `tuple`,
  `range`, or anything explicitly wrapped in `waypoint.seq(...)`.
  Plain generators can't be sliced or resumed without re-executing
  them from scratch, so `waypoint` raises a clear `NotResumableError`
  instead of silently failing to resume or resuming incorrectly. This
  constraint is documented loudly in the README, not buried.

- **Call-aware checkpoint keys.** The checkpoint key is derived from
  the function's qualified name plus a hash of the call arguments, so
  running the same function on different input never resumes into
  the wrong dataset, and running it again on the *same* input picks
  up the interrupted checkpoint.

- **Zero config by default.** Checkpoints live under `.waypoint/` next
  to wherever the script runs. Nothing to set up for the common case;
  the directory and key are configurable via decorator arguments for
  people who need it (Epic 2).

- **Atomic, corruption-safe writes.** Every checkpoint write is
  write-to-temp-file + `os.replace`, so a hard kill (`SIGKILL`, power
  loss) mid-write can never leave a partially-written file that fails
  to parse on the next run.

- **Success cleans up.** When the decorated function returns normally
  (the loop is exhausted, no exception), its checkpoint file is
  deleted. A finished run starts fresh next time; only an interrupted
  run resumes.

- **`waypoint` guarantees "don't redo completed iterations," not
  "exactly-once side effects."** If the process is killed mid-body
  (partway through processing one item), that item is retried on
  resume — the checkpoint only advances after an iteration completes.
  Side effects inside the loop body should be idempotent if that
  matters for the use case. This trade-off is documented, not hidden.

- **No daemon, no dependencies.** A plain JSON file is the entire
  state store. Nothing to install, run, or configure beyond
  `pip install waypoint`.

## What "v1 done" looks like

- `@checkpoint` applied to a script's `for` loop that gets interrupted
  with Ctrl-C partway through, then rerun, resumes at the correct
  index — no redone work, no re-triggered side effects for completed
  items.
- Test coverage includes: plain lists, `range`, nested function calls,
  an exception raised mid-loop (the failing item is retried, not
  skipped), and multiple independently-decorated functions/checkpoints
  coexisting in one script.
- Checkpoints are cleaned up automatically on success and are safe
  against a hard kill mid-write.
- Non-resumable loop shapes (bare generators) fail loudly with a
  actionable error rather than silently doing the wrong thing.
- Published to PyPI with a README that demonstrates the Ctrl-C/rerun
  behavior end-to-end.
