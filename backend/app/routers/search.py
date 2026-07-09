from fastapi import APIRouter, HTTPException, Query

from app.models import ScoredChunk
from app.retrieval.hybrid import hybrid_search

router = APIRouter()


@router.get("/api/search", response_model=list[ScoredChunk])
def search(
    tenant_id: str = Query(...),
    query: str = Query(...),
    k: int = Query(6, ge=1, le=50),
) -> list[ScoredChunk]:
    try:
        return hybrid_search(tenant_id, query, k=k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
