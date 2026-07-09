"""Shared test fixtures.

Tests never call the real OpenAI embeddings API (no network, no billing, no
key required in this environment). Every retrieval/ingestion function accepts
an injectable `embed_fn`, and tests supply this deterministic hashed
bag-of-words embedder instead. It is a real function producing real vectors
(not a mock of our own code) — good enough to prove tenant isolation and RRF
fusion behave correctly.
"""

import hashlib

import pytest

from app.qdrant_client import EMBEDDING_DIM
from app.retrieval import keyword


@pytest.fixture(autouse=True)
def _reset_keyword_state():
    """The per-tenant BM25 index is process-global by design (architecture
    calls for in-process, in-memory indexes) — reset it between tests so
    tenants from one test can't bleed term statistics into another."""
    keyword.reset()
    yield
    keyword.reset()


def _fake_embed_fn(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        vector = [0.0] * EMBEDDING_DIM
        for word in text.lower().split():
            idx = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIM
            vector[idx] += 1.0
        norm = sum(component * component for component in vector) ** 0.5 or 1.0
        vectors.append([component / norm for component in vector])
    return vectors


@pytest.fixture
def fake_embed_fn():
    return _fake_embed_fn
