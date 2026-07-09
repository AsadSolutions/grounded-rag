import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.qdrant_client import EMBEDDING_DIM, ensure_collection
from app.retrieval.dense import dense_search


@pytest.fixture
def qdrant_client():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    return client


def _upsert(client, embed_fn, tenant_id, text, doc_id="d1", index=0):
    chunk_id = str(uuid.uuid4())
    vector = embed_fn([text])[0]
    client.upsert(
        collection_name="chunks",
        points=[
            PointStruct(
                id=chunk_id,
                vector=vector,
                payload={
                    "chunk_id": chunk_id,
                    "tenant_id": tenant_id,
                    "doc_id": doc_id,
                    "doc_name": "a.txt",
                    "chunk_index": index,
                    "text": text,
                },
            )
        ],
    )
    return chunk_id


def test_dense_search_returns_scored_chunks_for_the_tenant(qdrant_client, fake_embed_fn):
    chunk_id = _upsert(qdrant_client, fake_embed_fn, "t1", "travel expense reimbursement policy")

    results = dense_search(
        "t1", "travel expense reimbursement policy", k=5, client=qdrant_client, embed_fn=fake_embed_fn
    )

    assert len(results) == 1
    assert results[0].chunk_id == chunk_id
    assert results[0].tenant_id == "t1"
    assert isinstance(results[0].score, float)


def test_dense_search_respects_k(qdrant_client, fake_embed_fn):
    for i in range(5):
        _upsert(qdrant_client, fake_embed_fn, "t1", f"document number {i} about travel policy", index=i)

    results = dense_search("t1", "travel policy", k=2, client=qdrant_client, embed_fn=fake_embed_fn)

    assert len(results) == 2


def test_dense_search_rejects_missing_tenant_id(qdrant_client, fake_embed_fn):
    with pytest.raises(ValueError):
        dense_search("", "any query", client=qdrant_client, embed_fn=fake_embed_fn)


def test_dense_search_returns_empty_for_unknown_tenant(qdrant_client, fake_embed_fn):
    _upsert(qdrant_client, fake_embed_fn, "t1", "travel expense reimbursement policy")

    results = dense_search("t2", "travel expense reimbursement policy", client=qdrant_client, embed_fn=fake_embed_fn)

    assert results == []


def test_embedding_dim_constant_matches_text_embedding_3_small():
    assert EMBEDDING_DIM == 1536
