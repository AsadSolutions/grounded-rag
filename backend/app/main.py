import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import chat, documents, eval, search, tenants
from app.tenant_registry import expire_scratch_tenants

logger = logging.getLogger(__name__)

EXPIRY_INTERVAL_SECONDS = 3600


async def _run_expiry_sweep() -> None:
    try:
        await expire_scratch_tenants()
    except Exception:
        logger.exception("Scratch tenant expiry sweep failed")


async def _expiry_loop() -> None:
    while True:
        await _run_expiry_sweep()
        await asyncio.sleep(EXPIRY_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_expiry_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(tenants.router)
app.include_router(eval.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
