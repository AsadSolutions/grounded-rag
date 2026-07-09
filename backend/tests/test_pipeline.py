import hashlib

import pytest
from qdrant_client import QdrantClient

from app.ingest.pipeline import ingest_document
from app.qdrant_client import COLLECTION_NAME, ensure_collection
from app.retrieval import keyword


@pytest.fixture
def qdrant_client():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    return client


def test_ingest_document_upserts_chunks_with_tenant_payload(qdrant_client, fake_embed_fn):
    result = ingest_document(
        tenant_id="t1",
        doc_name="handbook.txt",
        content=b"Employees accrue paid time off at a rate of one day per month.",
        client=qdrant_client,
        embed_fn=fake_embed_fn,
    )

    assert result.tenant_id == "t1"
    assert result.doc_name == "handbook.txt"
    assert result.chunk_count == 1

    count = qdrant_client.count(collection_name=COLLECTION_NAME).count
    assert count == 1

    points, _ = qdrant_client.scroll(collection_name=COLLECTION_NAME, limit=10, with_payload=True)
    assert points[0].payload["tenant_id"] == "t1"
    assert points[0].payload["doc_id"] == result.doc_id


def test_ingest_document_rebuilds_bm25_index_for_the_tenant(qdrant_client, fake_embed_fn):
    ingest_document(
        tenant_id="t1",
        doc_name="a.txt",
        content=b"Travel expense reimbursement requires manager approval within thirty days.",
        client=qdrant_client,
        embed_fn=fake_embed_fn,
    )
    ingest_document(
        tenant_id="t1",
        doc_name="b.txt",
        content=b"Office plants need watering twice a week during summer.",
        client=qdrant_client,
        embed_fn=fake_embed_fn,
    )
    ingest_document(
        tenant_id="t1",
        doc_name="c.txt",
        content=b"The quarterly financial report is finished and ready for review.",
        client=qdrant_client,
        embed_fn=fake_embed_fn,
    )

    results = keyword.keyword_search("t1", "travel expense reimbursement", k=5)

    assert results


def test_ingest_document_rejects_unsupported_file_type(qdrant_client, fake_embed_fn):
    with pytest.raises(ValueError):
        ingest_document(
            tenant_id="t1",
            doc_name="malware.exe",
            content=b"binary junk",
            client=qdrant_client,
            embed_fn=fake_embed_fn,
        )


def test_ingest_document_stamps_content_hash_on_every_chunk(qdrant_client, fake_embed_fn):
    content = b"first document text here spanning enough tokens for two chunks maybe not but that is fine"

    ingest_document(tenant_id="t1", doc_name="a.txt", content=content, client=qdrant_client, embed_fn=fake_embed_fn)

    expected_hash = hashlib.sha256(content).hexdigest()
    points, _ = qdrant_client.scroll(collection_name=COLLECTION_NAME, limit=10, with_payload=True)
    assert all(p.payload["content_hash"] == expected_hash for p in points)


def test_ingest_document_two_documents_get_distinct_doc_ids(qdrant_client, fake_embed_fn):
    first = ingest_document(
        tenant_id="t1", doc_name="a.txt", content=b"first document text here", client=qdrant_client, embed_fn=fake_embed_fn
    )
    second = ingest_document(
        tenant_id="t1", doc_name="b.txt", content=b"second document text here", client=qdrant_client, embed_fn=fake_embed_fn
    )

    assert first.doc_id != second.doc_id
