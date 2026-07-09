import pytest
from qdrant_client import QdrantClient

from app.models import Chunk
from app.qdrant_client import ensure_collection
from app.retrieval import keyword


def _chunk(tenant_id, chunk_id, text, doc_id="d1", index=0):
    return Chunk(
        chunk_id=chunk_id, tenant_id=tenant_id, doc_id=doc_id, doc_name="a.txt", chunk_index=index, text=text
    )


def test_keyword_search_ranks_by_term_overlap():
    keyword.add_chunks(
        "t1",
        [
            _chunk("t1", "c1", "the invoice number is 88213", index=0),
            _chunk("t1", "c2", "office plants need watering", index=1),
            _chunk("t1", "c3", "the quarterly report is finished", index=2),
        ],
    )

    results = keyword.keyword_search("t1", "invoice number", k=5)

    assert results
    assert results[0].chunk_id == "c1"


def test_keyword_search_isolates_tenants():
    keyword.add_chunks("t1", [_chunk("t1", "c1", "invoice number 88213")])
    keyword.add_chunks("t2", [_chunk("t2", "c2", "invoice number 88213")])

    results = keyword.keyword_search("t1", "invoice number", k=5)

    assert all(r.tenant_id == "t1" for r in results)


def test_keyword_search_no_match_returns_empty():
    keyword.add_chunks("t1", [_chunk("t1", "c1", "office plants need watering")])

    assert keyword.keyword_search("t1", "invoice number", k=5) == []


def test_keyword_search_unknown_tenant_returns_empty():
    # Unknown to the in-process cache too, so this exercises the lazy
    # rebuild-from-Qdrant path (empty in-memory Qdrant here) rather than a
    # real server — a client must be supplied explicitly for that lookup.
    client = QdrantClient(":memory:")
    ensure_collection(client)

    assert keyword.keyword_search("nope", "anything", k=5, client=client) == []


def test_keyword_search_rejects_missing_tenant_id():
    with pytest.raises(ValueError):
        keyword.keyword_search("", "anything")


def test_add_chunks_accumulates_across_calls():
    keyword.add_chunks("t1", [_chunk("t1", "c1", "invoice number 88213", index=0)])
    keyword.add_chunks(
        "t1",
        [
            _chunk("t1", "c2", "second document about the invoice", index=1),
            _chunk("t1", "c3", "office plants need watering", index=2),
        ],
    )

    results = keyword.keyword_search("t1", "invoice", k=5)

    assert {r.chunk_id for r in results} == {"c1", "c2"}


def test_chunk_count_reflects_added_chunks():
    assert keyword.chunk_count("t1") == 0

    keyword.add_chunks("t1", [_chunk("t1", "c1", "invoice number 88213")])

    assert keyword.chunk_count("t1") == 1


def test_forget_tenant_clears_only_that_tenant():
    keyword.add_chunks("t1", [_chunk("t1", "c1", "invoice number 88213")])
    keyword.add_chunks("t2", [_chunk("t2", "c2", "invoice number 88213")])

    keyword.forget_tenant("t1")

    assert keyword.chunk_count("t1") == 0
    assert keyword.chunk_count("t2") == 1
