from fastapi import APIRouter

from app.config import DEMO_TENANTS
from app.document_catalog import list_tenant_documents
from app.models import DemoTenantResponse, TenantResponse
from app.tenant_registry import create_scratch_tenant

router = APIRouter()


@router.post("/api/tenants", response_model=TenantResponse)
async def create_tenant() -> TenantResponse:
    record = await create_scratch_tenant()
    return TenantResponse(tenant_id=record.tenant_id, name="Scratch tenant", expires_at=record.expires_at)


@router.get("/api/tenants/demo", response_model=list[DemoTenantResponse])
def list_demo_tenants() -> list[DemoTenantResponse]:
    return [
        DemoTenantResponse(
            id=meta.id,
            name=meta.name,
            description=meta.description,
            document_count=len(list_tenant_documents(meta.id)),
            suggested_question=meta.suggested_question,
        )
        for meta in DEMO_TENANTS
    ]
