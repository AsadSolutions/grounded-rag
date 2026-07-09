"""app.ingest.seed: idempotent seeding of the two fixed demo tenants.

Uses synthetic temp-dir corpora rather than the real seed_docs content, so
these tests don't couple to prose that might be edited later — only to the
skip-by-content-hash and rebuild-BM25-once-per-tenant behavior.
"""

import pytest
from qdrant_client import QdrantClient

from app.ingest.seed import seed_demo_tenants
from app.qdrant_client import COLLECTION_NAME, ensure_collection
from app.retrieval import keyword


@pytest.fixture
def qdrant_client():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    return client


def _write_docs(base_dir, tenant_id, docs: dict[str, str]):
    tenant_dir = base_dir / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    for name, text in docs.items():
        (tenant_dir / name).write_text(text)
    return base_dir


_ACME_DOCS = {
    "a.md": "Policy POL-2201 covers billing rates and invoice cycles for the firm and its various matters handled by staff each quarter.",
    "b.md": "Policy POL-2210 covers confidentiality obligations for client data handling across all offices consistently and thoroughly.",
    "c.md": "Policy POL-2230 covers document retention schedules for client files kept by the records department for many years.",
}

_TECHCORP_DOCS = {
    "x.md": "The Atlas API rate limit is 600 requests per minute per key for all endpoints across every workspace plan.",
    "y.md": "Error code E-1042 indicates a sync conflict between two concurrent edits made to the same task record.",
    "z.md": "The free trial for Atlas lasts 14 days and requires no credit card upfront for any new workspace.",
}


def test_seed_ingests_all_files_for_each_tenant(tmp_path, qdrant_client, fake_embed_fn):
    _write_docs(tmp_path, "demo-acme-legal", _ACME_DOCS)
    _write_docs(tmp_path, "demo-techcorp", _TECHCORP_DOCS)

    summary = seed_demo_tenants(
        seed_dir=tmp_path,
        tenant_ids=["demo-acme-legal", "demo-techcorp"],
        client=qdrant_client,
        embed_fn=fake_embed_fn,
    )

    assert summary["demo-acme-legal"] == {"ingested": 3, "skipped": 0}
    assert summary["demo-techcorp"] == {"ingested": 3, "skipped": 0}
    assert qdrant_client.count(collection_name=COLLECTION_NAME).count == 6


def test_seed_is_idempotent_on_second_run(tmp_path, qdrant_client, fake_embed_fn):
    _write_docs(tmp_path, "demo-acme-legal", _ACME_DOCS)

    first = seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)
    second = seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)

    assert first["demo-acme-legal"]["ingested"] == 3
    assert second["demo-acme-legal"] == {"ingested": 0, "skipped": 3}
    assert qdrant_client.count(collection_name=COLLECTION_NAME).count == 3


def test_seed_reingests_a_file_whose_content_changed(tmp_path, qdrant_client, fake_embed_fn):
    _write_docs(tmp_path, "demo-acme-legal", _ACME_DOCS)
    seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)

    edited = dict(_ACME_DOCS)
    edited["a.md"] = edited["a.md"] + " This sentence was added in a later revision of the policy document."
    _write_docs(tmp_path, "demo-acme-legal", edited)

    summary = seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)

    assert summary["demo-acme-legal"]["ingested"] == 1
    assert summary["demo-acme-legal"]["skipped"] == 2


def test_seed_uses_fixed_tenant_ids_as_folder_names(tmp_path, qdrant_client, fake_embed_fn):
    _write_docs(tmp_path, "demo-acme-legal", _ACME_DOCS)

    seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)

    points, _ = qdrant_client.scroll(collection_name=COLLECTION_NAME, limit=100, with_payload=True)
    assert all(p.payload["tenant_id"] == "demo-acme-legal" for p in points)


def test_seed_rebuilds_bm25_even_when_all_files_are_skipped(tmp_path, qdrant_client, fake_embed_fn):
    _write_docs(tmp_path, "demo-acme-legal", _ACME_DOCS)
    seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)

    keyword.reset()  # simulate a fresh process: in-memory BM25 wiped, Qdrant untouched

    summary = seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)

    assert summary["demo-acme-legal"]["skipped"] == 3
    results = keyword.keyword_search("demo-acme-legal", "billing rates", k=5, client=qdrant_client)
    assert results


def test_seed_missing_tenant_folder_ingests_nothing(tmp_path, qdrant_client, fake_embed_fn):
    summary = seed_demo_tenants(seed_dir=tmp_path, tenant_ids=["demo-acme-legal"], client=qdrant_client, embed_fn=fake_embed_fn)

    assert summary["demo-acme-legal"] == {"ingested": 0, "skipped": 0}
