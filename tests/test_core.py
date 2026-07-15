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
