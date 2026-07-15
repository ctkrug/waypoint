# Contributing

Waypoint is a small, focused library — the fastest way to contribute is
usually a bug report or a small, well-tested pull request.

## Setup

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

## Before opening a PR

    ruff check src tests
    mypy src
    pytest

Keep pull requests scoped to one change. See `docs/BACKLOG.md` for the
current roadmap and `docs/VISION.md` for the design principles new
features should follow.
