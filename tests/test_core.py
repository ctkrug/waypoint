from waypoint import checkpoint


def test_checkpoint_preserves_function_behavior():
    @checkpoint
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_checkpoint_preserves_metadata():
    @checkpoint
    def example():
        """Docstring."""

    assert example.__name__ == "example"
    assert example.__doc__ == "Docstring."
