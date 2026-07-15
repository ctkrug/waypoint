"""Property-based tests for the two core invariants the library exists
to guarantee: resuming after an interruption reproduces the exact
original sequence, and a checkpoint always resumes the correct suffix.

These use a plain ``tempfile.TemporaryDirectory()`` per example rather
than the ``tmp_path`` fixture, since a function-scoped pytest fixture is
only set up once per test *function*, not once per hypothesis-generated
example -- reusing one directory across examples would let leftover
checkpoint state from one example leak into the next.
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from waypoint import checkpoint
from waypoint.loop_context import _LoopContext
from waypoint.storage import write_checkpoint


class _Interrupted(Exception):
    pass


@settings(deadline=None, max_examples=50)
@given(items=st.lists(st.integers(), min_size=1, max_size=25), data=st.data())
def test_interrupted_run_resumes_to_the_exact_original_sequence(items, data):
    kill_at = data.draw(st.integers(min_value=0, max_value=len(items) - 1))

    with tempfile.TemporaryDirectory() as tmp_dir:
        processed = []
        attempted = {"done": False}

        @checkpoint(dir=Path(tmp_dir))
        def process(values):
            for i, value in enumerate(values):
                if i == kill_at and not attempted["done"]:
                    attempted["done"] = True
                    raise _Interrupted()
                processed.append(value)

        with pytest.raises(_Interrupted):
            process(items)
        process(items)

        # No matter where the interruption landed, the rerun completes
        # the exact original sequence in order -- nothing skipped,
        # nothing duplicated.
        assert processed == items


@settings(deadline=None, max_examples=100)
@given(
    items=st.lists(st.integers(), max_size=30),
    resume_at=st.integers(min_value=0, max_value=100),
)
def test_track_always_resumes_the_correct_suffix(items, resume_at):
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "job.json"
        write_checkpoint(path, {"index": resume_at})

        ctx = _LoopContext(path)
        result = list(ctx.track(items, "for x in y:"))

        expected_start = min(resume_at, len(items))
        assert result == items[expected_start:]
