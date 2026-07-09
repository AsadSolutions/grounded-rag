from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.ingest.embed import embed_texts
from app.models import ScoredChunk
from app.qdrant_client import COLLECTION_NAME, get_qdrant_client


def dense_search(
    tenant_id: str,
    query: str,
    k: int = 10,
    client: QdrantClient | None = None,
    embed_fn=embed_texts,
) -> list[ScoredChunk]:
    if not tenant_id:
        raise ValueError("tenant_id is required for dense_search")

    client = client or get_qdrant_client()
    query_vector = embed_fn([query])[0]

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]),
        limit=k,
        with_payload=True,
    )

    return [ScoredChunk(**point.payload, score=point.score) for point in response.points]
