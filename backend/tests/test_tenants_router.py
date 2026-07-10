"""POST /api/tenants (scratch tenant creation) and GET /api/tenants/demo
(demo tenant listing with live Qdrant document counts)."""

from datetime import datetime, timedelta, timezone

import app.document_catalog as document_catalog
import app.tenant_registry as tenant_registry
from app.ingest.pipeline import ingest_document
from app.main import app
from app.qdrant_client import ensure_collection
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient


def test_create_tenant_returns_t_prefixed_id_and_24h_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(tenant_registry, "_STATE_PATH", tmp_path / "scratch_tenants.json")
    api = TestClient(app)

    resp = api.post("/api/tenants")

    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"].startswith("t_")
    assert body["name"]
    expires = datetime.fromisoformat(body["expires_at"])
    assert expires > datetime.now(timezone.utc) + timedelta(hours=23)


def test_list_demo_tenants_returns_configured_metadata_and_live_doc_count(monkeypatch, fake_embed_fn):
    memory_client = QdrantClient(":memory:")
    ensure_collection(memory_client)
    monkeypatch.setattr(document_catalog, "get_qdrant_client", lambda: memory_client)
    ingest_document(
        tenant_id="demo-acme-legal", doc_name="handbook.txt", content=b"Employees accrue paid time off.",
        client=memory_client, embed_fn=fake_embed_fn,
    )

    api = TestClient(app)
    resp = api.get("/api/tenants/demo")

    assert resp.status_code == 200
    body = resp.json()
    ids = {t["id"] for t in body}
    assert {"demo-acme-legal", "demo-techcorp"} <= ids
    acme = next(t for t in body if t["id"] == "demo-acme-legal")
    assert acme["document_count"] == 1
    assert acme["name"]
    assert acme["description"]
    assert acme["suggested_question"]

    techcorp = next(t for t in body if t["id"] == "demo-techcorp")
    assert techcorp["document_count"] == 0
