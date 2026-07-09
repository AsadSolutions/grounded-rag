import uuid

import tiktoken

from app.models import Chunk

_ENCODING = tiktoken.get_encoding("cl100k_base")


def chunk_text(
    text: str,
    *,
    tenant_id: str,
    doc_id: str,
    doc_name: str,
    chunk_size: int = 500,
    overlap: int = 75,
    content_hash: str | None = None,
) -> list[Chunk]:
    tokens = _ENCODING.encode(text)
    if not tokens:
        return []

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    start = 0
    index = 0
    while True:
        window = tokens[start : start + chunk_size]
        chunks.append(
            Chunk(
                chunk_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                doc_id=doc_id,
                doc_name=doc_name,
                chunk_index=index,
                text=_ENCODING.decode(window),
                content_hash=content_hash,
            )
        )
        if start + chunk_size >= len(tokens):
            break
        start += step
        index += 1

    return chunks
