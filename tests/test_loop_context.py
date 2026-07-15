import pytest

from waypoint import NotResumableError, Seq
from waypoint.loop_context import _LoopContext
from waypoint.storage import write_checkpoint


def test_track_iterates_all_items_on_fresh_checkpoint(tmp_path):
    ctx = _LoopContext(tmp_path / "job.json")
    assert list(ctx.track([10, 20, 30], "for x in y:")) == [10, 20, 30]


def test_track_resumes_from_persisted_index(tmp_path):
    path = tmp_path / "job.json"
    ctx = _LoopContext(path)
    for _ in ctx.track([10, 20, 30], "for x in y:"):
        ctx.advance()
        break  # only the first item "completes"

    resumed = _LoopContext(path)
    assert list(resumed.track([10, 20, 30], "for x in y:")) == [20, 30]


def test_advance_persists_incrementing_index(tmp_path):
    path = tmp_path / "job.json"
    ctx = _LoopContext(path)
    for _ in ctx.track([1, 2, 3], "for x in y:"):
        ctx.advance()

    from waypoint.storage import read_checkpoint

    assert read_checkpoint(path) == {"index": 3}


def test_cleanup_removes_checkpoint_file(tmp_path):
    path = tmp_path / "job.json"
    ctx = _LoopContext(path)
    ctx.advance()
    assert path.exists()

    ctx.cleanup()
    assert not path.exists()


def test_track_accepts_tuple_and_range(tmp_path):
    ctx = _LoopContext(tmp_path / "job.json")
    assert list(ctx.track((1, 2), "for x in y:")) == [1, 2]

    ctx2 = _LoopContext(tmp_path / "job2.json")
    assert list(ctx2.track(range(3), "for x in y:")) == [0, 1, 2]


def test_track_accepts_seq_wrapper(tmp_path):
    ctx = _LoopContext(tmp_path / "job.json")
    assert list(ctx.track(Seq([1, 2, 3]), "for x in y:")) == [1, 2, 3]


def test_track_rejects_generator_with_actionable_error(tmp_path):
    ctx = _LoopContext(tmp_path / "job.json")
    with pytest.raises(NotResumableError) as exc_info:
        ctx.track((x for x in range(3)), "for x in items:")

    message = str(exc_info.value)
    assert "for x in items:" in message
    assert "waypoint.seq" in message


def test_track_clips_stale_resume_index_to_sequence_length(tmp_path):
    path = tmp_path / "job.json"
    from waypoint.storage import write_checkpoint

    write_checkpoint(path, {"index": 999})
    ctx = _LoopContext(path)
    assert list(ctx.track([1, 2, 3], "for x in y:")) == []


def test_track_enumerate_yields_index_item_pairs_on_fresh_checkpoint(tmp_path):
    ctx = _LoopContext(tmp_path / "job.json")
    assert list(ctx.track_enumerate(["a", "b", "c"], "for i, x in y:")) == [
        (0, "a"),
        (1, "b"),
        (2, "c"),
    ]


def test_advance_invokes_on_progress_with_index_and_total(tmp_path):
    calls = []
    ctx = _LoopContext(tmp_path / "job.json", on_progress=lambda i, total: calls.append((i, total)))

    for _ in ctx.track([10, 20, 30], "for x in y:"):
        ctx.advance()

    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_advance_without_on_progress_does_not_raise(tmp_path):
    ctx = _LoopContext(tmp_path / "job.json")

    for _ in ctx.track([1, 2], "for x in y:"):
        ctx.advance()  # no callback configured -- must be a silent no-op


def test_interleaved_contexts_on_the_same_path_never_corrupt_the_file(tmp_path):
    # waypoint has no cross-call locking (documented: don't call the same
    # checkpointed function concurrently with identical arguments). But
    # even under that misuse, the on-disk file must always stay parseable
    # -- atomic replace should hold regardless of which context "wins".
    path = tmp_path / "job.json"
    ctx_a = _LoopContext(path)
    ctx_b = _LoopContext(path)
    iter_a = ctx_a.track([0, 1, 2, 3, 4], "for x in y:")
    iter_b = ctx_b.track([0, 1, 2, 3, 4], "for x in y:")

    from waypoint.storage import read_checkpoint

    turns = [
        (iter_a, ctx_a),
        (iter_b, ctx_b),
        (iter_a, ctx_a),
        (iter_b, ctx_b),
        (iter_b, ctx_b),
    ]
    for it, ctx in turns:
        next(it)
        ctx.advance()
        data = read_checkpoint(path)
        assert isinstance(data, dict)
        assert isinstance(data["index"], int)


def test_checkpoint_zero_index_is_valid_and_resumes_from_start(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": 0})

    ctx = _LoopContext(path)
    assert list(ctx.track([1, 2, 3], "for x in y:")) == [1, 2, 3]


def test_invalid_json_checkpoint_raises_actionable_error(tmp_path):
    path = tmp_path / "job.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(NotResumableError, match="not valid JSON"):
        _LoopContext(path)


def test_checkpoint_missing_index_key_raises_actionable_error(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"unexpected": "shape"})

    with pytest.raises(NotResumableError, match="unexpected format"):
        _LoopContext(path)


def test_checkpoint_non_dict_json_raises_actionable_error(tmp_path):
    path = tmp_path / "job.json"
    path.write_text("42", encoding="utf-8")

    with pytest.raises(NotResumableError, match="unexpected format"):
        _LoopContext(path)


def test_checkpoint_negative_index_raises_instead_of_silently_replaying(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": -5})

    with pytest.raises(NotResumableError, match="unexpected format"):
        _LoopContext(path)


def test_checkpoint_string_index_raises_actionable_error(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": "5"})

    with pytest.raises(NotResumableError, match="unexpected format"):
        _LoopContext(path)


def test_checkpoint_null_index_raises_actionable_error(tmp_path):
    path = tmp_path / "job.json"
    write_checkpoint(path, {"index": None})

    with pytest.raises(NotResumableError, match="unexpected format"):
        _LoopContext(path)


def test_track_enumerate_resumes_with_true_original_index(tmp_path):
    path = tmp_path / "job.json"
    ctx = _LoopContext(path)
    for _ in ctx.track_enumerate(["a", "b", "c"], "for i, x in y:"):
        ctx.advance()
        break  # only the first pair "completes"

    resumed = _LoopContext(path)
    assert list(resumed.track_enumerate(["a", "b", "c"], "for i, x in y:")) == [
        (1, "b"),
        (2, "c"),
    ]
