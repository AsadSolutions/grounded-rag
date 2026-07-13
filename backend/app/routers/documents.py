from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile

from app.config import get_settings
from app.document_catalog import delete_tenant_document, list_tenant_documents
from app.ingest.pipeline import ingest_document
from app.models import DocumentSummary, IngestResult
from app.rate_limit import RateLimiter
from app.tenant_guard import ensure_tenant_is_writable

router = APIRouter()

_upload_rate_limiter = RateLimiter(
    max_requests=get_settings().upload_rate_limit_per_minute, window_seconds=60
)


def _check_upload_rate_limit(request: Request) -> None:
    # Indirection (rather than `Depends(_upload_rate_limiter)` directly) so
    # tests can monkeypatch the module-level `_upload_rate_limiter` name and
    # have it take effect: FastAPI resolves a Depends() target once, at
    # route-definition time, so binding the object itself as the default
    # would freeze in the original instance forever.
    _upload_rate_limiter(request)


@router.post("/api/documents", response_model=IngestResult)
async def upload_document(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(_check_upload_rate_limit),
) -> IngestResult:
    ensure_tenant_is_writable(tenant_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        return ingest_document(tenant_id=tenant_id, doc_name=file.filename, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/documents", response_model=list[DocumentSummary])
def list_documents(tenant_id: str = Query(...)) -> list[DocumentSummary]:
    try:
        return list_tenant_documents(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, tenant_id: str = Query(...)) -> Response:
    ensure_tenant_is_writable(tenant_id)
    try:
        deleted = delete_tenant_document(tenant_id, doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found for tenant '{tenant_id}'")
    return Response(status_code=204)
