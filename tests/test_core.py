import functools

import pytest

from waypoint import checkpoint
from waypoint.core import _checkpoint_key


def test_checkpoint_preserves_function_behavior(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    @checkpoint
    def sum_all(items):
        total = 0
        for item in items:
            total += item
        return total

    assert sum_all([1, 2, 3]) == 6


def test_checkpoint_preserves_metadata():
    @checkpoint
    def example():
        """Docstring."""
        for _ in []:
            pass

    assert example.__name__ == "example"
    assert example.__doc__ == "Docstring."


def test_checkpoint_on_progress_reports_index_and_total(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []

    @checkpoint(on_progress=lambda index, total: calls.append((index, total)))
    def process(items):
        for item in items:
            pass

    process([10, 20, 30])

    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_checkpoint_without_on_progress_has_no_callback_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    @checkpoint
    def process(items):
        for item in items:
            pass

    process([1, 2, 3])  # no on_progress configured -- must not raise


def _func():
    pass


def test_checkpoint_key_is_stable_for_identical_calls():
    key_a = _checkpoint_key(_func, (1, 2), {"x": "y"})
    key_b = _checkpoint_key(_func, (1, 2), {"x": "y"})
    assert key_a == key_b


def test_checkpoint_key_differs_for_different_args():
    key_a = _checkpoint_key(_func, (1,), {})
    key_b = _checkpoint_key(_func, (2,), {})
    assert key_a != key_b


def test_checkpoint_key_differs_for_different_kwargs():
    key_a = _checkpoint_key(_func, (), {"n": 1})
    key_b = _checkpoint_key(_func, (), {"n": 2})
    assert key_a != key_b


def test_checkpoint_key_ignores_kwarg_order():
    key_a = _checkpoint_key(_func, (), {"a": 1, "b": 2})
    key_b = _checkpoint_key(_func, (), {"b": 2, "a": 1})
    assert key_a == key_b


def test_checkpoint_key_differs_for_different_functions():
    def other():
        pass

    key_a = _checkpoint_key(_func, (), {})
    key_b = _checkpoint_key(other, (), {})
    assert key_a != key_b


def test_checkpoint_key_includes_qualified_function_name():
    key = _checkpoint_key(_func, (), {})
    assert key.startswith(f"{_func.__module__}.{_func.__qualname__}-")


def test_checkpoint_composes_with_another_decorator_above_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def logged(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    @logged
    @checkpoint
    def process(items):
        seen = []
        for item in items:
            seen.append(item)
        return seen

    assert process([1, 2, 3]) == [1, 2, 3]


def test_checkpoint_on_a_class_method_resumes_correctly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class Worker:
        def __init__(self):
            self.log = []
            self.attempted = False

        @checkpoint
        def process(self, items):
            for item in items:
                if item == 2 and not self.attempted:
                    self.attempted = True
                    raise RuntimeError("boom")
                self.log.append(item)
            return self.log

    worker = Worker()
    with pytest.raises(RuntimeError):
        worker.process([1, 2, 3])
    assert worker.log == [1]

    worker.process([1, 2, 3])
    assert worker.log == [1, 2, 3]
