"""Tenant document catalog: list and delete, both derived from Qdrant
chunk payloads grouped by doc_id — there's no separate document table,
Qdrant chunk payloads are the only source of truth.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.models import Chunk, DocumentSummary
from app.qdrant_client import COLLECTION_NAME, get_qdrant_client
from app.retrieval import keyword

_SCROLL_PAGE_SIZE = 1000


def _tenant_filter(tenant_id: str) -> Filter:
    return Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])


def _scroll_tenant_chunks(tenant_id: str, client: QdrantClient) -> list[Chunk]:
    chunks: list[Chunk] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=_tenant_filter(tenant_id),
            limit=_SCROLL_PAGE_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        chunks.extend(Chunk(**point.payload) for point in points)
        if offset is None:
            break
    return chunks


def list_tenant_documents(tenant_id: str, client: QdrantClient | None = None) -> list[DocumentSummary]:
    if not tenant_id:
        raise ValueError("tenant_id is required for list_tenant_documents")

    client = client or get_qdrant_client()
    chunks = _scroll_tenant_chunks(tenant_id, client)

    by_doc: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        by_doc.setdefault(chunk.doc_id, []).append(chunk)

    summaries = []
    for doc_id, doc_chunks in by_doc.items():
        uploaded_ats = [c.uploaded_at for c in doc_chunks if c.uploaded_at]
        summaries.append(
            DocumentSummary(
                id=doc_id,
                tenant_id=tenant_id,
                name=doc_chunks[0].doc_name,
                chunk_count=len(doc_chunks),
                uploaded_at=min(uploaded_ats) if uploaded_ats else None,
            )
        )
    return sorted(summaries, key=lambda d: d.uploaded_at or "")


def delete_tenant_document(tenant_id: str, doc_id: str, client: QdrantClient | None = None) -> bool:
    if not tenant_id:
        raise ValueError("tenant_id is required for delete_tenant_document")

    client = client or get_qdrant_client()
    doc_filter = Filter(
        must=[
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
            FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
        ]
    )

    existing, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=doc_filter,
        limit=1,
        with_payload=False,
        with_vectors=False,
    )
    if not existing:
        return False

    client.delete(collection_name=COLLECTION_NAME, points_selector=doc_filter)
    keyword.rebuild_from_qdrant(tenant_id, client=client)
    return True
