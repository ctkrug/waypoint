from waypoint import Seq, seq


def test_seq_materializes_a_generator():
    wrapped = seq(x * 2 for x in range(4))
    assert isinstance(wrapped, Seq)
    assert wrapped.items == [0, 2, 4, 6]


def test_seq_of_empty_iterable_has_no_items():
    wrapped = seq(iter([]))
    assert wrapped.items == []
    assert len(wrapped) == 0


def test_seq_supports_len():
    wrapped = seq([1, 2, 3])
    assert len(wrapped) == 3


def test_seq_is_iterable():
    wrapped = seq(range(3))
    assert list(wrapped) == [0, 1, 2]


def test_seq_only_consumes_source_generator_once():
    def gen():
        yield 1
        yield 2

    source = gen()
    wrapped = seq(source)
    # The generator is exhausted during materialization, but Seq's own
    # items list can be iterated repeatedly.
    assert list(wrapped) == [1, 2]
    assert list(wrapped) == [1, 2]
