# Changelog

All notable changes to this project are documented here.
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-07-15

First stable release: the resumable-loop engine and its documented
constraints are locked in.

### Added

- `@checkpoint`: AST-based resumable-loop engine. Decorating a function
  whose body contains a single top-level `for item in <sequence>:` loop
  makes it resumable -- killing the process mid-run and rerunning with
  the same arguments picks up right after the last completed iteration.
- `waypoint.seq()` / `Seq`: materializes an arbitrary iterable (a
  generator, a cursor) into a resumable sequence.
- `@checkpoint(dir=..., key=...)`: configurable checkpoint directory and
  explicit key namespace.
- Atomic, corruption-safe checkpoint persistence under `.waypoint/`.
- `enumerate()`-wrapped loops: `for i, item in enumerate(items):` resumes
  with `i` reflecting the item's true original index.
- `@checkpoint(on_progress=...)`: optional `callback(index, total)` fired
  after each completed iteration.
- `python -m waypoint status|clear`: list stored checkpoints (key,
  progress index, last-modified time) or delete one by key.
- Initial project scaffold: package layout, CI, and planning docs.

### Fixed

- A checkpoint file that's invalid JSON, missing its `index` key, or has
  a negative/non-integer index (hand-edited, truncated, or written by an
  incompatible version) now raises a clear `NotResumableError` instead
  of crashing with a raw `JSONDecodeError`/`KeyError`/`TypeError` -- or,
  worse, a negative index silently replaying the wrong slice of the
  sequence.
- `python -m waypoint status` no longer crashes if one checkpoint file
  in the directory is corrupt; it now shows that entry as unreadable and
  keeps listing the rest.
- A loop body that `continue`s past the tracked item could desync the
  checkpoint from the sequence's true position: a later item completing
  in the same run would get checkpointed at an index that silently
  claimed the skipped item was done too, permanently dropping it (and
  duplicating later items) on the next run. `advance()` now only
  persists progress that's contiguous with what's already confirmed
  done, so a skipped item is always retried instead of lost.
