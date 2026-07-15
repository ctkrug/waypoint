from waypoint.__main__ import main
from waypoint.storage import write_checkpoint


def test_main_status_reports_checkpoint_under_custom_dir(tmp_path, capsys):
    write_checkpoint(tmp_path / "job.json", {"index": 7})

    code = main(["status", "--dir", str(tmp_path)])

    assert code == 0
    assert "job" in capsys.readouterr().out


def test_main_clear_removes_checkpoint_under_custom_dir(tmp_path, capsys):
    write_checkpoint(tmp_path / "job.json", {"index": 7})

    code = main(["clear", "job", "--dir", str(tmp_path)])

    assert code == 0
    assert not (tmp_path / "job.json").exists()


def test_main_clear_returns_nonzero_for_unknown_key(tmp_path):
    code = main(["clear", "missing", "--dir", str(tmp_path)])
    assert code == 1


def test_main_requires_a_subcommand():
    try:
        main([])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("expected argparse to exit for a missing subcommand")
