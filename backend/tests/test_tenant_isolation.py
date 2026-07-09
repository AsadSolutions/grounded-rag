"""The most important test in the repo.

Uploads documents as two different tenants into the same Qdrant collection
and proves tenant A's queries never return tenant B's chunks, across dense
search, keyword search, and the fused hybrid search — including adversarial
cases where a broken filter would be tempted to leak (near-duplicate text
across tenants, and a tenant whose only document is a weak semantic match
next to a competing tenant with many strong matches).
"""

import pytest
from qdrant_client import QdrantClient

from app.ingest.pipeline import ingest_document
from app.qdrant_client import ensure_collection
from app.retrieval.dense import dense_search
from app.retrieval.hybrid import hybrid_search
from app.retrieval.keyword import keyword_search


@pytest.fixture
def qdrant_client():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    return client


def _upload(client, embed_fn, tenant_id, doc_name, text):
    return ingest_document(
        tenant_id=tenant_id,
        doc_name=doc_name,
        content=text.encode("utf-8"),
        client=client,
        embed_fn=embed_fn,
    )


def test_dense_search_never_returns_other_tenants_chunks(qdrant_client, fake_embed_fn):
    _upload(
        qdrant_client,
        fake_embed_fn,
        "tenant-a",
        "acme.txt",
        "Acme Corp reimburses travel expenses within 30 days of a manager approved report.",
    )
    _upload(
        qdrant_client,
        fake_embed_fn,
        "tenant-b",
        "globex.txt",
        "Globex Industries offers unlimited paid time off after the first year of employment.",
    )

    results = dense_search(
        "tenant-a", "travel expense reimbursement policy", k=10, client=qdrant_client, embed_fn=fake_embed_fn
    )

    assert results, "expected at least one result for tenant-a"
    assert all(r.tenant_id == "tenant-a" for r in results)


def test_keyword_search_never_returns_other_tenants_chunks(qdrant_client, fake_embed_fn):
    # BM25 needs more than one document in a tenant's corpus for IDF to be
    # meaningful (a term appearing in every document of a tiny corpus scores
    # zero), so tenant-a gets two distractor docs alongside the target one.
    _upload(
        qdrant_client,
        fake_embed_fn,
        "tenant-a",
        "acme.txt",
        "Acme Corp reimburses travel expenses within 30 days of a manager approved report.",
    )
    _upload(qdrant_client, fake_embed_fn, "tenant-a", "handbook.txt", "Employees accrue paid time off monthly.")
    _upload(
        qdrant_client, fake_embed_fn, "tenant-a", "security.txt", "Passwords must be rotated every ninety days."
    )
    _upload(
        qdrant_client,
        fake_embed_fn,
        "tenant-b",
        "globex.txt",
        "Globex Industries offers unlimited paid time off after the first year of employment.",
    )

    results = keyword_search("tenant-a", "travel expense reimbursement", k=10)

    assert results
    assert all(r.tenant_id == "tenant-a" for r in results)


def test_hybrid_search_never_returns_other_tenants_chunks(qdrant_client, fake_embed_fn):
    _upload(
        qdrant_client,
        fake_embed_fn,
        "tenant-a",
        "acme.txt",
        "Acme Corp reimburses travel expenses within 30 days of a manager approved report.",
    )
    _upload(
        qdrant_client,
        fake_embed_fn,
        "tenant-b",
        "globex.txt",
        "Globex Industries offers unlimited paid time off after the first year of employment.",
    )

    results_a = hybrid_search(
        "tenant-a", "travel expense reimbursement policy", k=6, client=qdrant_client, embed_fn=fake_embed_fn
    )
    results_b = hybrid_search(
        "tenant-b", "paid time off policy", k=6, client=qdrant_client, embed_fn=fake_embed_fn
    )

    assert results_a and all(r.tenant_id == "tenant-a" for r in results_a)
    assert results_b and all(r.tenant_id == "tenant-b" for r in results_b)


def test_hybrid_search_does_not_leak_even_when_other_tenant_is_a_better_semantic_match(
    qdrant_client, fake_embed_fn
):
    # tenant-a owns one document that barely matches the query. tenant-b owns
    # five documents that match it almost exactly. A soft/optional tenant
    # filter would let tenant-b's stronger global ranking leak into tenant-a's
    # results. The mandatory filter must prevent that regardless of rank.
    _upload(qdrant_client, fake_embed_fn, "tenant-a", "unrelated.txt", "The office plant needs watering twice a week.")
    for i in range(5):
        _upload(
            qdrant_client,
            fake_embed_fn,
            "tenant-b",
            f"policy-{i}.txt",
            "Travel expense reimbursement requires a manager approved report submitted within 30 days.",
        )

    results = hybrid_search(
        "tenant-a", "travel expense reimbursement policy", k=6, client=qdrant_client, embed_fn=fake_embed_fn
    )

    assert all(r.tenant_id == "tenant-a" for r in results)


def test_isolation_holds_for_near_duplicate_content_across_tenants(qdrant_client, fake_embed_fn):
    # Identical text uploaded under two tenants rules out isolation that
    # accidentally works because the content itself happens to differ.
    _upload(qdrant_client, fake_embed_fn, "tenant-a", "dup.txt", "The password reset link expires after one hour.")
    _upload(qdrant_client, fake_embed_fn, "tenant-b", "dup.txt", "The password reset link expires after one hour.")

    results = hybrid_search(
        "tenant-b", "password reset link expiry", k=10, client=qdrant_client, embed_fn=fake_embed_fn
    )

    assert results
    assert all(r.tenant_id == "tenant-b" for r in results)


def test_dense_search_rejects_missing_tenant_id(qdrant_client, fake_embed_fn):
    with pytest.raises(ValueError):
        dense_search("", "any query", client=qdrant_client, embed_fn=fake_embed_fn)


def test_hybrid_search_rejects_missing_tenant_id(qdrant_client, fake_embed_fn):
    with pytest.raises(ValueError):
        hybrid_search("", "any query", client=qdrant_client, embed_fn=fake_embed_fn)
