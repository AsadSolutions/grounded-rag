from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.ingest.pipeline import ingest_document
from app.models import IngestResult
from app.tenant_guard import ensure_tenant_is_writable

router = APIRouter()


@router.post("/api/documents", response_model=IngestResult)
async def upload_document(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
) -> IngestResult:
    ensure_tenant_is_writable(tenant_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        return ingest_document(tenant_id=tenant_id, doc_name=file.filename, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
