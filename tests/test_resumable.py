"""End-to-end coverage of the wow moment: kill mid-loop, rerun, resume."""

import pytest

from waypoint import checkpoint


class _Interrupted(Exception):
    pass


def test_resumes_after_interruption_without_redoing_completed_items(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    processed = []
    attempt = {"count": 0}

    @checkpoint
    def process(items):
        for item in items:
            if item == 5 and attempt["count"] == 0:
                attempt["count"] += 1
                raise _Interrupted()
            processed.append(item)

    items = list(range(10))

    with pytest.raises(_Interrupted):
        process(items)

    assert processed == [0, 1, 2, 3, 4]

    process(items)

    assert processed == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_failed_item_is_retried_not_skipped_on_rerun(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    processed = []
    attempt = {"count": 0}

    @checkpoint
    def process(items):
        for item in items:
            if item == 2 and attempt["count"] == 0:
                attempt["count"] += 1
                raise _Interrupted()
            processed.append(item)

    items = [0, 1, 2, 3]

    with pytest.raises(_Interrupted):
        process(items)

    process(items)

    # item 2 appears exactly once -- retried after the failure, never
    # skipped and never duplicated.
    assert processed == [0, 1, 2, 3]
