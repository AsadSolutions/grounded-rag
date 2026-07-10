"""Scratch tenant lifecycle: creation, listing, and the hourly expiry sweep.

Scratch tenant records live in a small JSON state file rather than Qdrant,
because a scratch tenant can exist with zero documents (nothing to filter
on in Qdrant yet) but still needs a trackable expiry from the moment it's
created — this is the "small JSON state file" ARCHITECTURE.md anticipates
alongside Qdrant payloads. Demo tenants are never stored here: they're
permanent, protected, and never expire.

Writes are atomic: `_save` writes to a temp file in the same directory and
`os.replace`s it into place, so a crash mid-write can never truncate or
corrupt the file — a reader always sees either the fully-old or fully-new
generation. Writes are also serialized behind a single `asyncio.Lock`,
since both `POST /api/tenants` and the hourly expiry sweep write this same
file and could otherwise race and lose an update (last-write-wins on two
concurrent read-modify-write cycles). The lock only provides real mutual
exclusion because every writer is a coroutine that runs directly on the
event loop rather than in a worker thread — `asyncio.Lock` has no
cross-thread guarantee, so none of these functions may be dispatched
through `run_in_threadpool`.
"""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from starlette.concurrency import run_in_threadpool

from app.qdrant_client import COLLECTION_NAME, get_qdrant_client
from app.retrieval import keyword
from app.tenant_guard import is_protected_tenant

SCRATCH_TENANT_PREFIX = "t_"
SCRATCH_TENANT_TTL = timedelta(hours=24)
_STATE_PATH = Path(__file__).resolve().parent / "data" / "scratch_tenants.json"

_write_lock = asyncio.Lock()


class ScratchTenantRecord(BaseModel):
    tenant_id: str
    created_at: str
    expires_at: str


def _resolve_path(path: Path | None) -> Path:
    return path or _STATE_PATH


def _load(path: Path) -> list[ScratchTenantRecord]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [ScratchTenantRecord(**item) for item in data]


def _save(path: Path, records: list[ScratchTenantRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps([r.model_dump() for r in records], indent=2))
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


async def create_scratch_tenant(path: Path | None = None) -> ScratchTenantRecord:
    path = _resolve_path(path)
    now = datetime.now(timezone.utc)
    record = ScratchTenantRecord(
        tenant_id=f"{SCRATCH_TENANT_PREFIX}{uuid.uuid4().hex}",
        created_at=now.isoformat(),
        expires_at=(now + SCRATCH_TENANT_TTL).isoformat(),
    )
    async with _write_lock:
        records = _load(path)
        records.append(record)
        _save(path, records)
    return record


def list_scratch_tenants(path: Path | None = None) -> list[ScratchTenantRecord]:
    return _load(_resolve_path(path))


async def remove_scratch_tenant(tenant_id: str, path: Path | None = None) -> None:
    path = _resolve_path(path)
    async with _write_lock:
        records = [r for r in _load(path) if r.tenant_id != tenant_id]
        _save(path, records)


async def expire_scratch_tenants(
    now: datetime | None = None,
    client: QdrantClient | None = None,
    path: Path | None = None,
) -> list[str]:
    now = now or datetime.now(timezone.utc)
    client = client or get_qdrant_client()
    path = _resolve_path(path)

    async with _write_lock:
        records = _load(path)

        expired_ids: list[str] = []
        remaining: list[ScratchTenantRecord] = []
        for record in records:
            expires_at = datetime.fromisoformat(record.expires_at)
            if expires_at <= now and not is_protected_tenant(record.tenant_id):
                expired_ids.append(record.tenant_id)
            else:
                remaining.append(record)

        for tenant_id in expired_ids:
            tenant_filter = Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])
            await run_in_threadpool(client.delete, collection_name=COLLECTION_NAME, points_selector=tenant_filter)
            keyword.forget_tenant(tenant_id)

        _save(path, remaining)

    return expired_ids
