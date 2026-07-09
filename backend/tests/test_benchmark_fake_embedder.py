from benchmarks.fake_embedder import fast_fake_embed


def test_returns_one_vector_per_text():
    vectors = fast_fake_embed(["a", "b", "c"])
    assert len(vectors) == 3


def test_vectors_have_the_configured_embedding_dimension():
    from app.qdrant_client import EMBEDDING_DIM

    vectors = fast_fake_embed(["hello world"])
    assert len(vectors[0]) == EMBEDDING_DIM


def test_empty_input_returns_empty_list():
    assert fast_fake_embed([]) == []


def test_vectors_are_unit_normalized():
    vectors = fast_fake_embed(["some text", "more text"])
    for vector in vectors:
        norm = sum(component * component for component in vector) ** 0.5
        assert abs(norm - 1.0) < 1e-6


def test_handles_a_large_batch_quickly():
    import time

    start = time.perf_counter()
    vectors = fast_fake_embed([f"document number {i}" for i in range(5000)])
    elapsed = time.perf_counter() - start

    assert len(vectors) == 5000
    assert elapsed < 5.0
