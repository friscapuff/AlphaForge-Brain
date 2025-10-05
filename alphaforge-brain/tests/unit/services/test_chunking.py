from services import chunking as ch


def test_chunk_exact_division():
    # coverage: services.chunking exact division using iter_chunk_slices
    n = 10
    slices = list(ch.iter_chunk_slices(n, 5))
    # Expect two slices covering full range without overlap
    assert slices == [(0, 5, 0), (5, 10, 0)]


def test_chunk_with_remainder():
    # coverage: services.chunking remainder branch
    slices = list(ch.iter_chunk_slices(9, 4))
    # (0,4,0),(4,8,0),(8,9,0)
    assert slices == [(0, 4, 0), (4, 8, 0), (8, 9, 0)]


def test_chunk_single_element():
    slices = list(ch.iter_chunk_slices(1, 10))
    assert slices == [(0, 1, 0)]


def test_chunk_empty_iterable():
    slices = list(ch.iter_chunk_slices(0, 3))
    assert slices == []


def test_chunk_oversize_batch():
    slices = list(ch.iter_chunk_slices(5, 100))
    assert slices == [(0, 5, 0)]
