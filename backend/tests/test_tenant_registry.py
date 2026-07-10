"""Scratch tenant registry: creation, listing, removal, and the hourly
expiry sweep that deletes expired scratch tenants' Qdrant chunks and BM25
cache while leaving demo tenants untouched.

create_scratch_tenant/remove_scratch_tenant/expire_scratch_tenants are
async (they hold the module's shared write lock across their read-modify-
write of the JSON state file), so they're driven here via asyncio.run —
this project has no pytest-asyncio/pytest-anyio plugin installed, and
asyncio.run is the plain-stdlib way to call a coroutine from a sync test,
already established in tests/test_main.py.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from app.ingest.pipeline import ingest_document
from app.qdrant_client import COLLECTION_NAME, ensure_collection
from app.retrieval import keyword
from app.tenant_registry import (
    ScratchTenantRecord,
    _load,
    _save,
    create_scratch_tenant,
    expire_scratch_tenants,
    list_scratch_tenants,
    remove_scratch_tenant,
)
from qdrant_client import QdrantClient


def test_create_scratch_tenant_has_t_prefix_and_24h_expiry(tmp_path):
    path = tmp_path / "scratch_tenants.json"

    record = asyncio.run(create_scratch_tenant(path=path))

    assert record.tenant_id.startswith("t_")
    created = datetime.fromisoformat(record.created_at)
    expires = datetime.fromisoformat(record.expires_at)
    assert expires - created == timedelta(hours=24)


def test_list_scratch_tenants_returns_created_records(tmp_path):
    path = tmp_path / "scratch_tenants.json"
    record = asyncio.run(create_scratch_tenant(path=path))

    listed = list_scratch_tenants(path=path)

    assert [r.tenant_id for r in listed] == [record.tenant_id]


def test_list_scratch_tenants_empty_when_no_file_yet(tmp_path):
    path = tmp_path / "scratch_tenants.json"

    assert list_scratch_tenants(path=path) == []


def test_remove_scratch_tenant_drops_only_that_record(tmp_path):
    path = tmp_path / "scratch_tenants.json"
    keep = asyncio.run(create_scratch_tenant(path=path))
    drop = asyncio.run(create_scratch_tenant(path=path))

    asyncio.run(remove_scratch_tenant(drop.tenant_id, path=path))

    listed = list_scratch_tenants(path=path)
    assert [r.tenant_id for r in listed] == [keep.tenant_id]


def test_expire_scratch_tenants_deletes_expired_chunks_but_not_demo_tenant(tmp_path, fake_embed_fn):
    path = tmp_path / "scratch_tenants.json"
    client = QdrantClient(":memory:")
    ensure_collection(client)

    scratch_id = "t_expired0000000000000000"
    now = datetime.now(timezone.utc)
    path.write_text(
        json.dumps(
            [
                {
                    "tenant_id": scratch_id,
                    "created_at": (now - timedelta(hours=25)).isoformat(),
                    "expires_at": (now - timedelta(hours=1)).isoformat(),
                }
            ]
        )
    )

    ingest_document(
        tenant_id=scratch_id, doc_name="scratch.txt", content=b"Scratch tenant content about paid time off.",
        client=client, embed_fn=fake_embed_fn,
    )
    ingest_document(
        tenant_id="demo-acme-legal", doc_name="handbook.txt", content=b"Demo tenant content about paid time off.",
        client=client, embed_fn=fake_embed_fn,
    )

    removed = asyncio.run(expire_scratch_tenants(now=now, client=client, path=path))

    assert removed == [scratch_id]

    points, _ = client.scroll(collection_name=COLLECTION_NAME, limit=100, with_payload=True)
    remaining_tenant_ids = {p.payload["tenant_id"] for p in points}
    assert scratch_id not in remaining_tenant_ids
    assert "demo-acme-legal" in remaining_tenant_ids

    assert keyword.chunk_count(scratch_id) == 0
    assert keyword.chunk_count("demo-acme-legal") > 0
    assert list_scratch_tenants(path=path) == []


def test_expire_scratch_tenants_leaves_unexpired_tenant_alone(tmp_path):
    path = tmp_path / "scratch_tenants.json"
    client = QdrantClient(":memory:")
    ensure_collection(client)
    record = asyncio.run(create_scratch_tenant(path=path))

    removed = asyncio.run(expire_scratch_tenants(now=datetime.now(timezone.utc), client=client, path=path))

    assert removed == []
    assert [r.tenant_id for r in list_scratch_tenants(path=path)] == [record.tenant_id]


def test_save_is_atomic_a_failed_write_cannot_corrupt_or_truncate_existing_state(tmp_path, monkeypatch):
    path = tmp_path / "scratch_tenants.json"
    original = [
        ScratchTenantRecord(
            tenant_id="t_original",
            created_at="2026-01-01T00:00:00+00:00",
            expires_at="2026-01-02T00:00:00+00:00",
        )
    ]
    _save(path, original)

    def _boom(*args, **kwargs):
        raise OSError("simulated crash during the atomic replace")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(OSError):
        _save(path, [])

    # The previously-committed file must be completely untouched: no
    # partial write, no truncation, no corrupted JSON. A crash between
    # "temp file written" and "renamed into place" must never be visible
    # at `path` at all — that's the entire point of the atomic replace.
    assert _load(path) == original
    assert json.loads(path.read_text()) == [r.model_dump() for r in original]

    # No leftover temp file either — the failure path cleans up after itself.
    leftover = [p for p in path.parent.iterdir() if p.name != path.name]
    assert leftover == []
