# Backlog

Epics and stories for building waypoint to v1. See `docs/VISION.md`
for the design this backlog implements. Stories in Epic 1 are the wow
moment — they land first, before any ergonomics or polish work.

## Epic 1 — Core resumable-loop engine

- [x] **1.1 (WOW) Implement `@checkpoint` with AST-based iterable rewrite and disk-backed resume**
  - Given a script with `@checkpoint` over `for item in range(1000): slow(item)`,
    killing the process at item 500 and rerunning it skips items 0-499
    and resumes at item 500.
  - On normal completion (loop exhausted, no exception), the
    checkpoint file for that call is deleted, so a fresh rerun starts
    at 0.

- [x] **1.2 Checkpoint key derivation from function identity + call arguments**
  - Calling the same decorated function with different arguments
    produces distinct checkpoint files (no cross-contamination).
  - Calling with identical arguments after an interruption reuses the
    same checkpoint file and resumes it.

- [x] **1.3 Atomic, corruption-safe checkpoint writes**
  - Killing the process (`SIGKILL`) during a checkpoint write never
    leaves a corrupted/partial checkpoint file that fails to parse on
    the next run.
  - Checkpoint writes use write-to-temp + `os.replace` so a reader
    never observes a half-written file.

- [x] **1.4 Clear failure mode for non-resumable iterables**
  - Decorating a loop over a plain generator raises a descriptive
    `NotResumableError` at call time rather than silently failing to
    resume.
  - The error message names the offending loop and suggests wrapping
    it with `waypoint.seq(...)` or converting it to a list.

## Epic 2 — Ergonomics & configuration

- [x] **2.1 `waypoint.seq()` wrapper for arbitrary iterables**
  - `waypoint.seq(some_generator())` materializes it to a list once
    and is accepted by an `@checkpoint`-decorated loop.
  - A documented example shows converting a non-resumable generator
    loop into a resumable one with `waypoint.seq(...)`.

- [x] **2.2 Configurable checkpoint directory and key namespace**
  - `@checkpoint(dir=".state", key="job-42")` writes to
    `.state/job-42.json` instead of the default `.waypoint/` location.
  - Two decorated functions with distinct explicit keys never collide,
    even with identical source.

- [x] **2.3 CLI helper: `python -m waypoint status|clear`**
  - `python -m waypoint status` lists every checkpoint file under
    `.waypoint/` with function name, progress index, and
    last-modified time.
  - `python -m waypoint clear <key>` deletes the matching checkpoint
    so the next run starts fresh.

## Epic 3 — Robustness & real-world loop shapes

- [x] **3.1 Support `enumerate()`-wrapped loops**
  - A loop written as `for i, item in enumerate(items):` resumes
    correctly, with `i` reflecting the true original index after
    resume.
  - Existing bare-loop (`for item in items:`) tests continue to pass
    with no regression.

- [x] **3.2 Progress reporting hook**
  - `@checkpoint(on_progress=callback)` invokes
    `callback(index, total)` after each completed iteration.
  - Omitting `on_progress` has zero behavior change and zero added
    overhead versus not passing it.

- [x] **3.3 Exception-safe partial-iteration handling**
  - If the loop body raises mid-iteration, the checkpoint records the
    last *completed* index, not the failed one, so a rerun retries the
    failed item rather than skipping it.
  - A test simulates a transient failure on item N and confirms the
    rerun retries item N rather than starting at N+1.

## Epic 4 — Packaging, docs & release readiness

- [x] **4.1 Full README with quickstart and Ctrl-C demo**
  - The README quickstart snippet runs verbatim end-to-end and
    produces the documented resume behavior when copy-pasted.
  - The README prominently documents the "must be a concrete
    sequence" constraint rather than burying it.

- [x] **4.2 Packaging polish for PyPI**
  - `python -m build` produces a valid sdist and wheel that install
    cleanly into a fresh virtualenv via `pip install`.
  - `pip show waypoint` reports the correct version, license, and
    description after install.

- [ ] **4.3 CI matrix across supported Python versions**
  - CI passes on Python 3.9-3.12 via the GitHub Actions matrix.
  - The README CI badge reflects the current status of the `main`
    branch workflow.
