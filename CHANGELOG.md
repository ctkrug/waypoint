# Changelog

All notable changes to this project are documented here.
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
- Initial project scaffold: package layout, CI, and planning docs.
