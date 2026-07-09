from app.config import get_settings
from app.ingest.embed import embed_texts
from app.models import ScoredChunk
from app.retrieval.dense import dense_search
from app.retrieval.keyword import keyword_search


def hybrid_search(
    tenant_id: str,
    query: str,
    k: int = 6,
    dense_k: int = 10,
    keyword_k: int = 10,
    client=None,
    embed_fn=embed_texts,
    rrf_k: int | None = None,
) -> list[ScoredChunk]:
    if not tenant_id:
        raise ValueError("tenant_id is required for hybrid_search")

    rrf_k = get_settings().rrf_k if rrf_k is None else rrf_k

    dense_results = dense_search(tenant_id, query, k=dense_k, client=client, embed_fn=embed_fn)
    keyword_results = keyword_search(tenant_id, query, k=keyword_k, client=client)

    scores: dict[str, float] = {}
    chunks_by_id: dict[str, ScoredChunk] = {}

    for rank, chunk in enumerate(dense_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (rrf_k + rank + 1)
        chunks_by_id[chunk.chunk_id] = chunk

    for rank, chunk in enumerate(keyword_results):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (rrf_k + rank + 1)
        chunks_by_id.setdefault(chunk.chunk_id, chunk)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [chunks_by_id[chunk_id].model_copy(update={"score": scores[chunk_id]}) for chunk_id in ranked_ids[:k]]
