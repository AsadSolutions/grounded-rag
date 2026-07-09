import hashlib
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.ingest.chunk import chunk_text
from app.ingest.embed import embed_texts
from app.ingest.extract import extract_text
from app.models import IngestResult
from app.qdrant_client import COLLECTION_NAME, ensure_collection, get_qdrant_client
from app.retrieval import keyword


def ingest_document(
    *,
    tenant_id: str,
    doc_name: str,
    content: bytes,
    client: QdrantClient | None = None,
    embed_fn=embed_texts,
) -> IngestResult:
    if not tenant_id:
        raise ValueError("tenant_id is required for ingest_document")

    client = client or get_qdrant_client()
    ensure_collection(client)

    doc_id = str(uuid.uuid4())
    content_hash = hashlib.sha256(content).hexdigest()
    text = extract_text(doc_name, content)
    chunks = chunk_text(text, tenant_id=tenant_id, doc_id=doc_id, doc_name=doc_name, content_hash=content_hash)
    if not chunks:
        raise ValueError(f"No chunks produced for {doc_name}")

    vectors = embed_fn([chunk.text for chunk in chunks])
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(id=chunk.chunk_id, vector=vector, payload=chunk.model_dump())
            for chunk, vector in zip(chunks, vectors)
        ],
    )

    keyword.add_chunks(tenant_id, chunks)

    return IngestResult(doc_id=doc_id, doc_name=doc_name, tenant_id=tenant_id, chunk_count=len(chunks))
