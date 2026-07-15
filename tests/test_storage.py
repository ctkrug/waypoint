import os

import pytest

from waypoint.storage import (
    DEFAULT_CHECKPOINT_DIR,
    checkpoint_path,
    delete_checkpoint,
    read_checkpoint,
    write_checkpoint,
)


def test_checkpoint_path_uses_default_directory():
    path = checkpoint_path("my-job")
    assert path == DEFAULT_CHECKPOINT_DIR / "my-job.json"


def test_checkpoint_path_accepts_custom_directory(tmp_path):
    path = checkpoint_path("my-job", directory=tmp_path)
    assert path == tmp_path / "my-job.json"


def test_read_checkpoint_returns_none_when_missing(tmp_path):
    assert read_checkpoint(tmp_path / "absent.json") is None


def test_write_then_read_round_trips_data(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": 42})
    assert read_checkpoint(path) == {"index": 42}


def test_write_checkpoint_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "job.json"
    write_checkpoint(path, {"index": 1})
    assert path.exists()
    assert read_checkpoint(path) == {"index": 1}


def test_write_checkpoint_overwrites_existing_data(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": 1})
    write_checkpoint(path, {"index": 2})
    assert read_checkpoint(path) == {"index": 2}


def test_write_checkpoint_leaves_no_temp_files_behind(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": 1})
    assert os.listdir(tmp_path) == ["job.json"]


def test_failed_replace_does_not_corrupt_existing_checkpoint(tmp_path, monkeypatch):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": 1})

    def boom(*args, **kwargs):
        raise OSError("simulated failure during replace")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        write_checkpoint(path, {"index": 2})

    # The original checkpoint is untouched and still parses cleanly -- a
    # failed replace never leaves a torn write in its place.
    assert read_checkpoint(path) == {"index": 1}
    assert os.listdir(tmp_path) == ["job.json"]


def test_delete_checkpoint_removes_file(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": 1})
    delete_checkpoint(path)
    assert not path.exists()


def test_delete_checkpoint_is_noop_when_missing(tmp_path):
    delete_checkpoint(tmp_path / "absent.json")
