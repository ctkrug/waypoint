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


def test_outer_loop_resumes_while_inner_loop_is_left_untouched(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    processed = []
    attempt = {"count": 0}

    @checkpoint
    def process(rows):
        for row in rows:
            if row == [3, 3] and attempt["count"] == 0:
                attempt["count"] += 1
                raise _Interrupted()
            for cell in row:
                processed.append(cell)

    rows = [[1, 1], [2, 2], [3, 3], [4, 4]]

    with pytest.raises(_Interrupted):
        process(rows)

    assert processed == [1, 1, 2, 2]

    process(rows)

    # The outer (tracked) loop resumes at row [3, 3] instead of redoing
    # rows 0-1; the untracked inner loop still runs in full for every row
    # it does reach.
    assert processed == [1, 1, 2, 2, 3, 3, 4, 4]


def test_break_exits_the_loop_and_still_cleans_up_the_checkpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    @checkpoint
    def process(items):
        seen = []
        for item in items:
            if item == 3:
                break
            seen.append(item)
        return seen

    result = process([1, 2, 3, 4, 5])

    assert result == [1, 2]
    # A break is a deliberate, successful exit -- the function returned
    # normally, so the checkpoint is cleared just like any other
    # successful completion.
    checkpoint_dir = tmp_path / DEFAULT_CHECKPOINT_DIR
    assert list(checkpoint_dir.glob("*.json")) == []


def test_resuming_a_checkpoint_already_at_full_completion_self_heals(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    processed = []

    @checkpoint
    def process(items):
        for item in items:
            processed.append(item)

    items = [1, 2, 3]
    checkpoint_dir = tmp_path / DEFAULT_CHECKPOINT_DIR
    checkpoint_dir.mkdir()

    from waypoint.core import _checkpoint_key
    from waypoint.storage import checkpoint_path, write_checkpoint

    key = _checkpoint_key(process.__wrapped__, (items,), {})
    write_checkpoint(checkpoint_path(key, checkpoint_dir), {"index": len(items)})

    # Simulates a process killed right after the last advance() but
    # before cleanup() ran: the leftover checkpoint says every item is
    # already done, so the rerun does nothing and then cleans up.
    process(items)

    assert processed == []
    assert list(checkpoint_dir.glob("*.json")) == []


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
