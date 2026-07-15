import pytest

from waypoint.ast_transform import build_factory
from waypoint.exceptions import NotResumableError


class _RecordingCtx:
    def __init__(self):
        self.tracked = []
        self.advanced = 0

    def track(self, iterable, source):
        self.tracked.append((iterable, source))
        return iter(iterable)

    def advance(self):
        self.advanced += 1


def _process(items):
    seen = []
    for item in items:
        seen.append(item)
    return seen


def test_build_factory_rewrites_loop_to_use_context():
    ctx = _RecordingCtx()
    transformed = build_factory(_process)(ctx)

    assert transformed([1, 2, 3]) == [1, 2, 3]
    assert ctx.advanced == 3
    assert ctx.tracked == [([1, 2, 3], "for item in items:")]


def test_build_factory_leaves_loop_body_untouched_on_empty_input():
    ctx = _RecordingCtx()
    transformed = build_factory(_process)(ctx)

    assert transformed([]) == []
    assert ctx.advanced == 0


def _no_loop(x):
    return x + 1


def test_build_factory_raises_when_no_top_level_loop():
    with pytest.raises(NotResumableError, match="could not find a top-level"):
        build_factory(_no_loop)


def _tuple_target_loop(pairs):
    for key, value in pairs:
        pass


def test_build_factory_raises_for_unpacking_loop_target():
    with pytest.raises(NotResumableError, match="unpacking target"):
        build_factory(_tuple_target_loop)


def _make_closure_over_helper():
    log = []

    def helper(x):
        log.append(x * 2)

    def process(items):
        for item in items:
            helper(item)
        return log

    return process, log


def test_build_factory_preserves_closures_over_helper_functions():
    process, log = _make_closure_over_helper()
    ctx = _RecordingCtx()
    transformed = build_factory(process)(ctx)

    result = transformed([1, 2, 3])
    assert result == [2, 4, 6]
    assert log == [2, 4, 6]
    assert ctx.advanced == 3
