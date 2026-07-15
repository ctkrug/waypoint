"""End-to-end coverage of the wow moment: kill mid-loop, rerun, resume."""

import pytest

from waypoint import NotResumableError, checkpoint, seq
from waypoint.storage import DEFAULT_CHECKPOINT_DIR


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


def test_successful_completion_deletes_the_checkpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    @checkpoint
    def process(items):
        for item in items:
            pass

    process([1, 2, 3])

    checkpoint_dir = tmp_path / DEFAULT_CHECKPOINT_DIR
    assert list(checkpoint_dir.glob("*.json")) == []


def test_rerun_after_success_starts_fresh(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    processed = []

    @checkpoint
    def process(items):
        for item in items:
            processed.append(item)

    process([1, 2, 3])
    process([1, 2, 3])

    # No leftover checkpoint from the first run, so the second run
    # reprocesses every item rather than resuming past the end.
    assert processed == [1, 2, 3, 1, 2, 3]


def test_distinct_call_arguments_get_distinct_checkpoints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    @checkpoint
    def process(items):
        for item in items:
            if item == 1:
                raise _Interrupted()

    with pytest.raises(_Interrupted):
        process([0, 1, 2])
    with pytest.raises(_Interrupted):
        process([10, 1, 12])

    checkpoint_dir = tmp_path / DEFAULT_CHECKPOINT_DIR
    assert len(list(checkpoint_dir.glob("*.json"))) == 2


def test_independently_decorated_functions_do_not_collide(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a_seen, b_seen = [], []
    attempt = {"count": 0}

    @checkpoint
    def task_a(items):
        for item in items:
            if item == 1 and attempt["count"] == 0:
                attempt["count"] += 1
                raise _Interrupted()
            a_seen.append(item)

    @checkpoint
    def task_b(items):
        for item in items:
            b_seen.append(item)

    with pytest.raises(_Interrupted):
        task_a([0, 1, 2])
    task_b([0, 1, 2])

    assert a_seen == [0]
    assert b_seen == [0, 1, 2]

    task_a([0, 1, 2])
    assert a_seen == [0, 1, 2]


def test_loop_body_calling_a_closed_over_helper_resumes_correctly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log = []
    attempt = {"count": 0}

    def slow_call(item):
        if item == 2 and attempt["count"] == 0:
            attempt["count"] += 1
            raise _Interrupted()
        log.append(item * 10)

    @checkpoint
    def process(items):
        for item in items:
            slow_call(item)

    items = [1, 2, 3]

    with pytest.raises(_Interrupted):
        process(items)
    assert log == [10]

    process(items)
    assert log == [10, 20, 30]


def test_generator_loop_raises_not_resumable_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    @checkpoint
    def process(items):
        for item in items:
            pass

    with pytest.raises(NotResumableError):
        process(x for x in range(5))


def test_enumerate_loop_resumes_with_true_original_index(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    processed = []
    attempt = {"count": 0}

    @checkpoint
    def process(items):
        for i, item in enumerate(items):
            if item == "c" and attempt["count"] == 0:
                attempt["count"] += 1
                raise _Interrupted()
            processed.append((i, item))

    items = ["a", "b", "c", "d"]

    with pytest.raises(_Interrupted):
        process(items)

    assert processed == [(0, "a"), (1, "b")]

    process(items)

    assert processed == [(0, "a"), (1, "b"), (2, "c"), (3, "d")]


def test_seq_wrapped_generator_becomes_resumable(tmp_path, monkeypatch):
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

    def source():
        yield from range(5)

    with pytest.raises(_Interrupted):
        process(seq(source()))

    assert processed == [0, 1]

    process(seq(source()))

    assert processed == [0, 1, 2, 3, 4]
