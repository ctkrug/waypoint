import pytest

from waypoint import checkpoint


class _Interrupted(Exception):
    pass


def test_custom_dir_writes_under_that_directory(tmp_path):
    custom_dir = tmp_path / "state"

    @checkpoint(dir=custom_dir)
    def process(items):
        for item in items:
            if item == 1:
                raise _Interrupted()

    with pytest.raises(_Interrupted):
        process([0, 1, 2])

    assert list(custom_dir.glob("*.json"))
    assert not (tmp_path / ".waypoint").exists()


def test_custom_key_writes_expected_filename(tmp_path):
    @checkpoint(dir=tmp_path, key="job-42")
    def process(items):
        for item in items:
            if item == 1:
                raise _Interrupted()

    with pytest.raises(_Interrupted):
        process([0, 1, 2])

    assert (tmp_path / "job-42.json").exists()


def test_distinct_explicit_keys_never_collide(tmp_path):
    seen_a, seen_b = [], []

    @checkpoint(dir=tmp_path, key="a")
    def task_a(items):
        for item in items:
            seen_a.append(item)

    @checkpoint(dir=tmp_path, key="b")
    def task_b(items):
        for item in items:
            seen_b.append(item)

    task_a([1, 2])
    task_b([3, 4])

    assert seen_a == [1, 2]
    assert seen_b == [3, 4]


def test_unicode_and_emoji_key_round_trips(tmp_path):
    processed = []
    attempt = {"count": 0}

    @checkpoint(dir=tmp_path, key="jöb-🚀-42")
    def process(items):
        for item in items:
            if item == 1 and attempt["count"] == 0:
                attempt["count"] += 1
                raise _Interrupted()
            processed.append(item)

    with pytest.raises(_Interrupted):
        process([0, 1, 2])

    assert (tmp_path / "jöb-🚀-42.json").exists()

    process([0, 1, 2])
    assert processed == [0, 1, 2]


def test_same_explicit_key_resumes_across_different_call_shapes(tmp_path):
    processed = []
    attempt = {"count": 0}

    @checkpoint(dir=tmp_path, key="shared")
    def process(items):
        for item in items:
            if item == 1 and attempt["count"] == 0:
                attempt["count"] += 1
                raise _Interrupted()
            processed.append(item)

    with pytest.raises(_Interrupted):
        process([0, 1, 2])

    # A different call shape (extra trailing item) but the same explicit
    # key still resumes from the persisted index rather than restarting.
    process([0, 1, 2, 3])

    assert processed == [0, 1, 2, 3]
