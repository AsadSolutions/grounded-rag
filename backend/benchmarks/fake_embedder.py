"""Fast synthetic embedder for the scale benchmark.

The per-word sha256 hashing embedder used in the unit test suite (see
tests/conftest.py) is fine at a handful of chunks per test but would be a
real bottleneck at benchmark scale (tens of thousands of chunks). This
generates unit-normalized random vectors in a single vectorized numpy call
per batch — semantically meaningless, but that's fine here: the benchmark
measures ingestion/search/BM25 *system* performance, not embedding quality,
and the salted-fact retrieval checks are carried by exact-match BM25 keyword
search regardless of what the dense vectors look like.
"""

import numpy as np

from app.qdrant_client import EMBEDDING_DIM


def fast_fake_embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    rng = np.random.default_rng()
    vectors = rng.random((len(texts), EMBEDDING_DIM), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    return vectors.tolist()
