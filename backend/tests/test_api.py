"""End-to-end HTTP wiring: upload a document, then search for it.

This is the automated equivalent of the Phase 1 exit check ("curl a search
endpoint, get sensible fused results"). It swaps in an in-memory Qdrant
client and the deterministic fake embedder at the router boundary so it
never needs a real Qdrant server or an OpenAI key.
"""

import app.routers.documents as documents_router
import app.routers.search as search_router
from app.ingest.pipeline import ingest_document
from app.main import app
from app.qdrant_client import ensure_collection
from app.retrieval.hybrid import hybrid_search
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient


def _wire_fakes(monkeypatch, fake_embed_fn):
    memory_client = QdrantClient(":memory:")
    ensure_collection(memory_client)

    def fake_ingest(*, tenant_id, doc_name, content):
        return ingest_document(
            tenant_id=tenant_id, doc_name=doc_name, content=content, client=memory_client, embed_fn=fake_embed_fn
        )

    def fake_search(tenant_id, query, k=6):
        return hybrid_search(tenant_id, query, k=k, client=memory_client, embed_fn=fake_embed_fn)

    monkeypatch.setattr(documents_router, "ingest_document", fake_ingest)
    monkeypatch.setattr(search_router, "hybrid_search", fake_search)


def test_upload_then_search_round_trip(monkeypatch, fake_embed_fn):
    _wire_fakes(monkeypatch, fake_embed_fn)
    api = TestClient(app)

    upload_resp = api.post(
        "/api/documents",
        data={"tenant_id": "t1"},
        files={"file": ("handbook.txt", b"Employees accrue paid time off at a rate of one day per month.", "text/plain")},
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["tenant_id"] == "t1"

    search_resp = api.get("/api/search", params={"tenant_id": "t1", "query": "paid time off"})
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert results
    assert all(r["tenant_id"] == "t1" for r in results)


def test_upload_rejects_empty_file(monkeypatch, fake_embed_fn):
    _wire_fakes(monkeypatch, fake_embed_fn)
    api = TestClient(app)

    resp = api.post("/api/documents", data={"tenant_id": "t1"}, files={"file": ("a.txt", b"", "text/plain")})

    assert resp.status_code == 400


def test_upload_rejects_unsupported_file_type(monkeypatch, fake_embed_fn):
    _wire_fakes(monkeypatch, fake_embed_fn)
    api = TestClient(app)

    resp = api.post(
        "/api/documents", data={"tenant_id": "t1"}, files={"file": ("malware.exe", b"binary junk", "application/octet-stream")}
    )

    assert resp.status_code == 400


def test_upload_accepts_pdf(monkeypatch, fake_embed_fn):
    from pypdf import PdfWriter
    import io

    _wire_fakes(monkeypatch, fake_embed_fn)
    api = TestClient(app)

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # A blank page has no text layer; this still proves the router accepts
    # the .pdf extension and surfaces pypdf's own "no extractable text"
    # error rather than rejecting the upload outright.
    buffer = io.BytesIO()
    writer.write(buffer)

    resp = api.post("/api/documents", data={"tenant_id": "t1"}, files={"file": ("doc.pdf", buffer.getvalue(), "application/pdf")})

    assert resp.status_code == 400
    assert "No extractable text" in resp.json()["detail"]


def test_search_rejects_missing_tenant_id(monkeypatch, fake_embed_fn):
    _wire_fakes(monkeypatch, fake_embed_fn)
    api = TestClient(app)

    resp = api.get("/api/search", params={"tenant_id": "", "query": "anything"})

    assert resp.status_code == 400


def test_upload_to_demo_tenant_is_rejected(monkeypatch, fake_embed_fn):
    _wire_fakes(monkeypatch, fake_embed_fn)
    api = TestClient(app)

    resp = api.post(
        "/api/documents",
        data={"tenant_id": "demo-acme-legal"},
        files={"file": ("handbook.txt", b"some content", "text/plain")},
    )

    assert resp.status_code == 403
    assert "demo-acme-legal" in resp.json()["detail"]


def test_upload_to_scratch_tenant_is_allowed(monkeypatch, fake_embed_fn):
    _wire_fakes(monkeypatch, fake_embed_fn)
    api = TestClient(app)

    resp = api.post(
        "/api/documents",
        data={"tenant_id": "scratch-abc123"},
        files={"file": ("handbook.txt", b"Employees accrue paid time off at a rate of one day per month.", "text/plain")},
    )

    assert resp.status_code == 200
    assert resp.json()["tenant_id"] == "scratch-abc123"
