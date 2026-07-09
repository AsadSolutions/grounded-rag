import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(_ENV_FILE)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    qdrant_url: str
    embedding_model: str = "text-embedding-3-small"
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 75
    rrf_k: int = 60
    chat_model: str = "gpt-4o-mini"
    protected_tenant_ids: tuple[str, ...] = ("demo-acme-legal", "demo-techcorp")


@lru_cache
def get_settings() -> Settings:
    protected_env = os.environ.get("PROTECTED_TENANT_IDS")
    settings_kwargs = {
        "openai_api_key": os.environ.get("OPENAI_API_KEY") or None,
        "qdrant_url": os.environ.get("QDRANT_URL", "http://localhost:6333"),
    }
    if protected_env is not None:
        settings_kwargs["protected_tenant_ids"] = tuple(
            tenant_id.strip() for tenant_id in protected_env.split(",") if tenant_id.strip()
        )
    return Settings(**settings_kwargs)
