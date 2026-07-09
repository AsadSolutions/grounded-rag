"""FIX 1: the in-process BM25 index is lost on server restart while chunks
survive in Qdrant. This proves the lazy-rebuild-on-miss behavior: the first
keyword/hybrid query after a simulated restart transparently rebuilds the
tenant's index from Qdrant instead of silently returning nothing.
"""

import pytest
from qdrant_client import QdrantClient

from app.ingest.pipeline import ingest_document
from app.qdrant_client import ensure_collection
from app.retrieval import keyword
from app.retrieval.hybrid import hybrid_search
from app.retrieval.keyword import keyword_search


@pytest.fixture
def qdrant_client():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    return client


def _seed(client, embed_fn, tenant_id):
    ingest_document(
        tenant_id=tenant_id,
        doc_name="a.txt",
        content=b"Travel expense reimbursement requires manager approval within thirty days.",
        client=client,
        embed_fn=embed_fn,
    )
    ingest_document(
        tenant_id=tenant_id,
        doc_name="b.txt",
        content=b"Office plants need watering twice a week during summer.",
        client=client,
        embed_fn=embed_fn,
    )
    ingest_document(
        tenant_id=tenant_id,
        doc_name="c.txt",
        content=b"The quarterly financial report is finished and ready for review.",
        client=client,
        embed_fn=embed_fn,
    )


def test_keyword_search_lazily_rebuilds_after_simulated_restart(qdrant_client, fake_embed_fn):
    _seed(qdrant_client, fake_embed_fn, "t1")

    keyword.reset()  # simulates a process restart: in-memory BM25 wiped, Qdrant untouched

    results = keyword_search("t1", "travel expense reimbursement", k=5, client=qdrant_client)

    assert results
    assert all(r.tenant_id == "t1" for r in results)


def test_hybrid_search_still_returns_keyword_matches_after_simulated_restart(qdrant_client, fake_embed_fn):
    _seed(qdrant_client, fake_embed_fn, "t1")

    keyword.reset()

    results = hybrid_search("t1", "travel expense reimbursement", k=5, client=qdrant_client, embed_fn=fake_embed_fn)

    assert results
    assert all(r.tenant_id == "t1" for r in results)


def test_lazy_rebuild_hits_qdrant_once_then_caches(qdrant_client, fake_embed_fn):
    _seed(qdrant_client, fake_embed_fn, "t1")
    keyword.reset()

    scroll_calls = {"count": 0}
    real_scroll = qdrant_client.scroll

    def counting_scroll(*args, **kwargs):
        scroll_calls["count"] += 1
        return real_scroll(*args, **kwargs)

    qdrant_client.scroll = counting_scroll

    keyword_search("t1", "travel expense", k=5, client=qdrant_client)
    keyword_search("t1", "quarterly report", k=5, client=qdrant_client)

    assert scroll_calls["count"] == 1


def test_lazy_rebuild_of_unknown_tenant_does_not_error_and_caches_empty(qdrant_client):
    results = keyword_search("nonexistent-tenant", "anything", k=5, client=qdrant_client)

    assert results == []


def test_restart_isolation_still_holds_across_tenants(qdrant_client, fake_embed_fn):
    _seed(qdrant_client, fake_embed_fn, "tenant-a")
    _seed(qdrant_client, fake_embed_fn, "tenant-b")

    keyword.reset()

    results = keyword_search("tenant-a", "travel expense reimbursement", k=10, client=qdrant_client)

    assert results
    assert all(r.tenant_id == "tenant-a" for r in results)
