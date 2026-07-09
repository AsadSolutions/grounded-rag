"""rebuild_from_qdrant must page through the entire tenant corpus, not just
the first scroll page. A tenant with more chunks than a single page would
otherwise get a silently incomplete BM25 index after every restart.
"""

import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.qdrant_client import COLLECTION_NAME, ensure_collection
from app.retrieval import keyword
from app.retrieval.keyword import keyword_search, rebuild_from_qdrant


@pytest.fixture
def qdrant_client():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    return client


def _upsert_raw_chunks(client, tenant_id, count):
    points = []
    for i in range(count):
        chunk_id = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=chunk_id,
                vector=[0.0] * 1536,
                payload={
                    "chunk_id": chunk_id,
                    "tenant_id": tenant_id,
                    "doc_id": f"doc-{i}",
                    "doc_name": f"doc-{i}.txt",
                    "chunk_index": 0,
                    "text": f"filler text number {i} about routine business matters",
                    "content_hash": None,
                },
            )
        )
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def test_rebuild_retrieves_more_chunks_than_a_single_scroll_page(qdrant_client):
    # Must exceed a single scroll page under any reasonable page size choice
    # to actually exercise pagination rather than accidentally fitting in one.
    _upsert_raw_chunks(qdrant_client, "t1", 12_000)

    rebuild_from_qdrant("t1", client=qdrant_client)

    assert len(keyword._tenant_chunks["t1"]) == 12_000  # noqa: SLF001


def test_a_chunk_beyond_the_first_page_is_still_searchable(qdrant_client):
    _upsert_raw_chunks(qdrant_client, "t1", 12_000)
    # Give the very last chunk a distinctive, searchable term instead of the
    # generic filler shared by every other chunk.
    marker_id = str(uuid.uuid4())
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=marker_id,
                vector=[0.0] * 1536,
                payload={
                    "chunk_id": marker_id,
                    "tenant_id": "t1",
                    "doc_id": "doc-marker",
                    "doc_name": "doc-marker.txt",
                    "chunk_index": 0,
                    "text": "zzzuniquemarkerzzz appears nowhere else in this corpus",
                    "content_hash": None,
                },
            )
        ],
    )

    rebuild_from_qdrant("t1", client=qdrant_client)

    results = keyword_search("t1", "zzzuniquemarkerzzz", k=5, client=qdrant_client)
    assert any(r.chunk_id == marker_id for r in results)
