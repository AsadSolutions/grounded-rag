"""GET /api/documents (listing) and DELETE /api/documents/{doc_id}
(tenant-filtered delete, BM25 rebuild, demo tenant protection)."""

import app.document_catalog as document_catalog
from app.ingest.pipeline import ingest_document
from app.main import app
from app.qdrant_client import ensure_collection
from app.retrieval import keyword
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient


def _wire_fake_client(monkeypatch, memory_client):
    monkeypatch.setattr(document_catalog, "get_qdrant_client", lambda: memory_client)
    return memory_client


def test_list_documents_returns_tenant_docs(monkeypatch, fake_embed_fn):
    memory_client = QdrantClient(":memory:")
    ensure_collection(memory_client)
    _wire_fake_client(monkeypatch, memory_client)
    result = ingest_document(
        tenant_id="t1", doc_name="handbook.txt", content=b"Employees accrue paid time off.",
        client=memory_client, embed_fn=fake_embed_fn,
    )

    api = TestClient(app)
    resp = api.get("/api/documents", params={"tenant_id": "t1"})

    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) == 1
    assert docs[0]["id"] == result.doc_id
    assert docs[0]["tenant_id"] == "t1"
    assert docs[0]["name"] == "handbook.txt"
    assert docs[0]["chunk_count"] == result.chunk_count


def test_list_documents_empty_for_unknown_tenant(monkeypatch, fake_embed_fn):
    memory_client = QdrantClient(":memory:")
    ensure_collection(memory_client)
    _wire_fake_client(monkeypatch, memory_client)

    api = TestClient(app)
    resp = api.get("/api/documents", params={"tenant_id": "nobody"})

    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_document_removes_chunks_and_rebuilds_bm25(monkeypatch, fake_embed_fn):
    memory_client = QdrantClient(":memory:")
    ensure_collection(memory_client)
    _wire_fake_client(monkeypatch, memory_client)
    result = ingest_document(
        tenant_id="t1", doc_name="handbook.txt", content=b"Employees accrue paid time off.",
        client=memory_client, embed_fn=fake_embed_fn,
    )

    api = TestClient(app)
    resp = api.delete(f"/api/documents/{result.doc_id}", params={"tenant_id": "t1"})

    assert resp.status_code == 204
    assert keyword.chunk_count("t1") == 0
    remaining, _ = memory_client.scroll(collection_name="chunks", limit=100, with_payload=True)
    assert remaining == []


def test_delete_document_404s_for_unknown_doc(monkeypatch, fake_embed_fn):
    memory_client = QdrantClient(":memory:")
    ensure_collection(memory_client)
    _wire_fake_client(monkeypatch, memory_client)

    api = TestClient(app)
    resp = api.delete("/api/documents/does-not-exist", params={"tenant_id": "t1"})

    assert resp.status_code == 404


def test_delete_document_rejects_demo_tenant(monkeypatch, fake_embed_fn):
    memory_client = QdrantClient(":memory:")
    ensure_collection(memory_client)
    _wire_fake_client(monkeypatch, memory_client)
    result = ingest_document(
        tenant_id="demo-acme-legal", doc_name="handbook.txt", content=b"Employees accrue paid time off.",
        client=memory_client, embed_fn=fake_embed_fn,
    )

    api = TestClient(app)
    resp = api.delete(f"/api/documents/{result.doc_id}", params={"tenant_id": "demo-acme-legal"})

    assert resp.status_code == 403
    remaining, _ = memory_client.scroll(collection_name="chunks", limit=100, with_payload=True)
    assert remaining
