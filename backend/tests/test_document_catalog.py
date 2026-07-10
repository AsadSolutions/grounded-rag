"""list_tenant_documents / delete_tenant_document: pure functions over
Qdrant chunk payloads, grouped by doc_id (there's no separate document
table — Qdrant chunk payloads are the only source of truth), tenant-filtered.
"""

import pytest
from qdrant_client import QdrantClient

from app.document_catalog import delete_tenant_document, list_tenant_documents
from app.ingest.pipeline import ingest_document
from app.qdrant_client import ensure_collection


def test_list_tenant_documents_requires_tenant_id():
    with pytest.raises(ValueError):
        list_tenant_documents("")


def test_list_tenant_documents_groups_by_doc_id(fake_embed_fn):
    client = QdrantClient(":memory:")
    ensure_collection(client)
    result = ingest_document(
        tenant_id="t1",
        doc_name="handbook.txt",
        content=b"Employees accrue paid time off at a rate of one day per month.",
        client=client,
        embed_fn=fake_embed_fn,
    )

    docs = list_tenant_documents("t1", client=client)

    assert len(docs) == 1
    assert docs[0].id == result.doc_id
    assert docs[0].tenant_id == "t1"
    assert docs[0].name == "handbook.txt"
    assert docs[0].chunk_count == result.chunk_count
    assert docs[0].uploaded_at is not None


def test_list_tenant_documents_isolates_by_tenant(fake_embed_fn):
    client = QdrantClient(":memory:")
    ensure_collection(client)
    ingest_document(tenant_id="t1", doc_name="a.txt", content=b"Tenant one content here.", client=client, embed_fn=fake_embed_fn)
    ingest_document(tenant_id="t2", doc_name="b.txt", content=b"Tenant two content here.", client=client, embed_fn=fake_embed_fn)

    docs = list_tenant_documents("t1", client=client)

    assert len(docs) == 1
    assert docs[0].name == "a.txt"


def test_list_tenant_documents_empty_for_unknown_tenant(fake_embed_fn):
    client = QdrantClient(":memory:")
    ensure_collection(client)

    assert list_tenant_documents("nobody", client=client) == []


def test_delete_tenant_document_removes_only_that_document(fake_embed_fn):
    client = QdrantClient(":memory:")
    ensure_collection(client)
    keep = ingest_document(tenant_id="t1", doc_name="keep.txt", content=b"Keep this document around.", client=client, embed_fn=fake_embed_fn)
    remove = ingest_document(tenant_id="t1", doc_name="remove.txt", content=b"Remove this document instead.", client=client, embed_fn=fake_embed_fn)

    deleted = delete_tenant_document("t1", remove.doc_id, client=client)

    assert deleted is True
    remaining = list_tenant_documents("t1", client=client)
    assert [d.id for d in remaining] == [keep.doc_id]


def test_delete_tenant_document_returns_false_for_unknown_doc(fake_embed_fn):
    client = QdrantClient(":memory:")
    ensure_collection(client)

    assert delete_tenant_document("t1", "does-not-exist", client=client) is False


def test_delete_tenant_document_does_not_touch_other_tenants(fake_embed_fn):
    client = QdrantClient(":memory:")
    ensure_collection(client)
    other = ingest_document(tenant_id="t2", doc_name="other.txt", content=b"Other tenant content.", client=client, embed_fn=fake_embed_fn)
    mine = ingest_document(tenant_id="t1", doc_name="mine.txt", content=b"My content here.", client=client, embed_fn=fake_embed_fn)

    delete_tenant_document("t1", mine.doc_id, client=client)

    remaining = list_tenant_documents("t2", client=client)
    assert [d.id for d in remaining] == [other.doc_id]
