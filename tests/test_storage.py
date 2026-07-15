from waypoint.storage import DEFAULT_CHECKPOINT_DIR, checkpoint_path


def test_checkpoint_path_uses_default_directory():
    path = checkpoint_path("my-job")
    assert path == DEFAULT_CHECKPOINT_DIR / "my-job.json"


def test_checkpoint_path_accepts_custom_directory(tmp_path):
    path = checkpoint_path("my-job", directory=tmp_path)
    assert path == tmp_path / "my-job.json"
