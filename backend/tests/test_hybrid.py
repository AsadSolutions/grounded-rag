import pytest

from app.models import Chunk
from app.retrieval import hybrid


def _chunk(chunk_id, tenant_id="t1", index=0, text="text"):
    return Chunk(chunk_id=chunk_id, tenant_id=tenant_id, doc_id="d1", doc_name="a.txt", chunk_index=index, text=text)


def test_rrf_combines_ranks_from_both_result_lists(monkeypatch):
    dense_results = [_score(_chunk("a"), 0.9), _score(_chunk("b"), 0.8), _score(_chunk("c"), 0.7)]
    keyword_results = [_score(_chunk("c"), 5.0), _score(_chunk("b"), 3.0)]

    monkeypatch.setattr(hybrid, "dense_search", lambda *a, **k: dense_results)
    monkeypatch.setattr(hybrid, "keyword_search", lambda *a, **k: keyword_results)

    results = hybrid.hybrid_search("t1", "query", k=3)

    # "b" is rank 1 in dense (index 1) and rank 1 in keyword (index 1) -> highest combined RRF score.
    # "c" is rank 2 in dense and rank 0 in keyword.
    # "a" only appears in dense, at rank 0.
    ids = [r.chunk_id for r in results]
    assert set(ids) == {"a", "b", "c"}
    assert ids[0] in {"b", "c"}  # both appear in both lists; top of ranking should be one of these


def test_rrf_score_matches_formula(monkeypatch):
    dense_results = [_score(_chunk("a"), 0.9)]
    keyword_results = [_score(_chunk("a"), 5.0)]

    monkeypatch.setattr(hybrid, "dense_search", lambda *a, **k: dense_results)
    monkeypatch.setattr(hybrid, "keyword_search", lambda *a, **k: keyword_results)

    results = hybrid.hybrid_search("t1", "query", k=3, rrf_k=60)

    expected = 1 / (60 + 1) + 1 / (60 + 1)
    assert results[0].chunk_id == "a"
    assert results[0].score == pytest.approx(expected)


def test_hybrid_search_respects_k(monkeypatch):
    dense_results = [_score(_chunk(str(i)), 1.0 - i * 0.01) for i in range(10)]
    monkeypatch.setattr(hybrid, "dense_search", lambda *a, **k: dense_results)
    monkeypatch.setattr(hybrid, "keyword_search", lambda *a, **k: [])

    results = hybrid.hybrid_search("t1", "query", k=4)

    assert len(results) == 4


def test_hybrid_search_dedupes_chunk_appearing_in_both_lists(monkeypatch):
    chunk = _chunk("a")
    monkeypatch.setattr(hybrid, "dense_search", lambda *a, **k: [_score(chunk, 0.9)])
    monkeypatch.setattr(hybrid, "keyword_search", lambda *a, **k: [_score(chunk, 5.0)])

    results = hybrid.hybrid_search("t1", "query", k=10)

    assert len(results) == 1


def test_hybrid_search_rejects_missing_tenant_id():
    with pytest.raises(ValueError):
        hybrid.hybrid_search("", "query")


def _score(chunk, score):
    from app.models import ScoredChunk

    return ScoredChunk(**chunk.model_dump(), score=score)
