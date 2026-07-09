"""Idempotent seeding of the two fixed demo tenants.

Tenant ids are load-bearing (the frontend references them directly) so they
are hardcoded here rather than derived from folder names, even though the
folder names happen to match today.

Idempotency is grounded in Qdrant itself, not a side-file, so it can't drift:
before ingesting a file, we check whether a chunk with that (tenant_id,
doc_name, content_hash) already exists. If so, the file is skipped.

This script writes directly to the demo tenants via ingest_document, bypassing
the HTTP-layer write guard in app.tenant_guard — that guard protects the
public API from writes, not this trusted, offline administrative script.
"""

import hashlib
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config import get_settings
from app.ingest.embed import embed_texts
from app.ingest.pipeline import ingest_document
from app.qdrant_client import COLLECTION_NAME, ensure_collection, get_qdrant_client
from app.retrieval import keyword

SEED_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "seed_docs"
TENANT_IDS = list(get_settings().protected_tenant_ids)


def _already_ingested(client: QdrantClient, tenant_id: str, doc_name: str, content_hash: str) -> bool:
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                FieldCondition(key="doc_name", match=MatchValue(value=doc_name)),
                FieldCondition(key="content_hash", match=MatchValue(value=content_hash)),
            ]
        ),
        limit=1,
        with_payload=False,
        with_vectors=False,
    )
    return len(points) > 0


def seed_demo_tenants(
    seed_dir: Path = SEED_DOCS_DIR,
    tenant_ids: list[str] = TENANT_IDS,
    client: QdrantClient | None = None,
    embed_fn=embed_texts,
) -> dict[str, dict[str, int]]:
    client = client or get_qdrant_client()
    ensure_collection(client)

    summary: dict[str, dict[str, int]] = {}
    for tenant_id in tenant_ids:
        tenant_dir = seed_dir / tenant_id
        ingested = 0
        skipped = 0
        for doc_path in sorted(tenant_dir.glob("*.md")) if tenant_dir.is_dir() else []:
            content = doc_path.read_bytes()
            content_hash = hashlib.sha256(content).hexdigest()
            if _already_ingested(client, tenant_id, doc_path.name, content_hash):
                skipped += 1
                continue
            ingest_document(
                tenant_id=tenant_id,
                doc_name=doc_path.name,
                content=content,
                client=client,
                embed_fn=embed_fn,
            )
            ingested += 1

        keyword.rebuild_from_qdrant(tenant_id, client=client)
        summary[tenant_id] = {"ingested": ingested, "skipped": skipped}

    return summary


if __name__ == "__main__":
    result = seed_demo_tenants()
    for tenant_id, counts in result.items():
        print(f"{tenant_id}: ingested={counts['ingested']} skipped={counts['skipped']}")
