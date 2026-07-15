import io

from waypoint import cli
from waypoint.storage import write_checkpoint


def test_status_reports_no_checkpoints_for_empty_directory(tmp_path):
    out = io.StringIO()
    code = cli.status(tmp_path / "missing", out)

    assert code == 0
    assert "No checkpoints" in out.getvalue()


def test_status_lists_key_index_and_mtime_per_checkpoint(tmp_path):
    write_checkpoint(tmp_path / "job-a.json", {"index": 5})
    write_checkpoint(tmp_path / "job-b.json", {"index": 12})

    out = io.StringIO()
    code = cli.status(tmp_path, out)
    lines = out.getvalue().splitlines()

    assert code == 0
    assert len(lines) == 2
    assert "job-a" in lines[0] and "index=5" in lines[0]
    assert "job-b" in lines[1] and "index=12" in lines[1]


def test_status_does_not_crash_on_corrupt_json_checkpoint(tmp_path):
    write_checkpoint(tmp_path / "good.json", {"index": 5})
    (tmp_path / "bad.json").write_text("{not valid json", encoding="utf-8")

    out = io.StringIO()
    code = cli.status(tmp_path, out)
    lines = out.getvalue().splitlines()

    assert code == 0
    assert len(lines) == 2
    assert any("good" in line and "index=5" in line for line in lines)
    assert any("bad" in line for line in lines)


def test_status_does_not_crash_on_non_object_json_checkpoint(tmp_path):
    (tmp_path / "weird.json").write_text("42", encoding="utf-8")

    out = io.StringIO()
    code = cli.status(tmp_path, out)

    assert code == 0
    assert "weird" in out.getvalue()


def test_status_ignores_non_json_files(tmp_path):
    write_checkpoint(tmp_path / "job.json", {"index": 1})
    (tmp_path / "notes.txt").write_text("not a checkpoint")

    out = io.StringIO()
    cli.status(tmp_path, out)

    assert out.getvalue().count("\n") == 1


def test_clear_removes_matching_checkpoint(tmp_path):
    write_checkpoint(tmp_path / "job-42.json", {"index": 3})

    out = io.StringIO()
    code = cli.clear("job-42", tmp_path, out)

    assert code == 0
    assert not (tmp_path / "job-42.json").exists()
    assert "Cleared" in out.getvalue()


def test_clear_reports_failure_for_unknown_key(tmp_path):
    out = io.StringIO()
    code = cli.clear("does-not-exist", tmp_path, out)

    assert code == 1
    assert "No checkpoint found" in out.getvalue()
