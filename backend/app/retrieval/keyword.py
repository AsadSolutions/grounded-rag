"""Per-tenant BM25 keyword search, cached in process, rebuilt on upload.

The index lives only in process memory, so a server restart wipes it while
the chunks themselves survive in Qdrant (the source of truth). On the first
search for a tenant whose index isn't cached, it's lazily rebuilt from that
tenant's chunk payloads in Qdrant before searching.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from rank_bm25 import BM25Okapi

from app.models import Chunk, ScoredChunk
from app.qdrant_client import COLLECTION_NAME, get_qdrant_client

_tenant_chunks: dict[str, list[Chunk]] = {}
_tenant_indexes: dict[str, BM25Okapi] = {}
_SCROLL_PAGE_SIZE = 1000


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _rebuild_index(tenant_id: str) -> None:
    chunks = _tenant_chunks.get(tenant_id, [])
    if chunks:
        _tenant_indexes[tenant_id] = BM25Okapi([_tokenize(c.text) for c in chunks])
    else:
        _tenant_indexes.pop(tenant_id, None)


def add_chunks(tenant_id: str, chunks: list[Chunk]) -> None:
    if not chunks:
        return
    _tenant_chunks.setdefault(tenant_id, []).extend(chunks)
    _rebuild_index(tenant_id)


def rebuild_from_qdrant(tenant_id: str, client: QdrantClient | None = None) -> None:
    client = client or get_qdrant_client()
    tenant_filter = Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])

    chunks: list[Chunk] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=tenant_filter,
            limit=_SCROLL_PAGE_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        chunks.extend(Chunk(**point.payload) for point in points)
        if offset is None:
            break

    _tenant_chunks[tenant_id] = chunks
    _rebuild_index(tenant_id)


def keyword_search(tenant_id: str, query: str, k: int = 10, client: QdrantClient | None = None) -> list[ScoredChunk]:
    if not tenant_id:
        raise ValueError("tenant_id is required for keyword_search")

    if tenant_id not in _tenant_chunks:
        rebuild_from_qdrant(tenant_id, client=client)

    index = _tenant_indexes.get(tenant_id)
    if index is None:
        return []

    chunks = _tenant_chunks[tenant_id]
    scores = index.get_scores(_tokenize(query))
    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
    return [
        ScoredChunk(**chunk.model_dump(), score=float(score))
        for chunk, score in ranked[:k]
        if score > 0
    ]


def chunk_count(tenant_id: str) -> int:
    return len(_tenant_chunks.get(tenant_id, []))


def forget_tenant(tenant_id: str) -> None:
    """Clear one tenant's cached chunks/index without disturbing others."""
    _tenant_chunks.pop(tenant_id, None)
    _tenant_indexes.pop(tenant_id, None)


def reset() -> None:
    """Test-only: clear all in-process tenant state."""
    _tenant_chunks.clear()
    _tenant_indexes.clear()
