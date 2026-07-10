from datetime import datetime, timezone

import tiktoken

from app.ingest.chunk import chunk_text
from app.models import Chunk

_ENCODING = tiktoken.get_encoding("cl100k_base")


def test_short_text_produces_a_single_chunk():
    chunks = chunk_text("hello world", tenant_id="t1", doc_id="d1", doc_name="a.txt")

    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].tenant_id == "t1"
    assert chunks[0].doc_id == "d1"
    assert chunks[0].doc_name == "a.txt"
    assert chunks[0].chunk_index == 0


def test_long_text_splits_into_multiple_chunks_with_overlap():
    # 2000 distinct tokens, well beyond the 500 token chunk size.
    text = " ".join(f"word{i}" for i in range(2000))

    chunks = chunk_text(text, tenant_id="t1", doc_id="d1", doc_name="a.txt", chunk_size=500, overlap=75)

    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # Consecutive chunks overlap by 75 tokens (the documented unit — words and
    # tokens aren't 1:1 under subword tokenization, so compare at token level).
    first_tokens = _ENCODING.encode(chunks[0].text)
    second_tokens = _ENCODING.encode(chunks[1].text)
    assert first_tokens[-75:] == second_tokens[:75]


def test_each_chunk_gets_a_unique_id():
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(text, tenant_id="t1", doc_id="d1", doc_name="a.txt")

    ids = {c.chunk_id for c in chunks}
    assert len(ids) == len(chunks)


def test_empty_text_produces_no_chunks():
    assert chunk_text("", tenant_id="t1", doc_id="d1", doc_name="a.txt") == []


def test_content_hash_defaults_to_none():
    chunks = chunk_text("hello world", tenant_id="t1", doc_id="d1", doc_name="a.txt")

    assert chunks[0].content_hash is None


def test_content_hash_is_stamped_onto_every_chunk_when_given():
    text = " ".join(f"word{i}" for i in range(2000))

    chunks = chunk_text(text, tenant_id="t1", doc_id="d1", doc_name="a.txt", content_hash="abc123")

    assert len(chunks) > 1
    assert all(c.content_hash == "abc123" for c in chunks)


def test_chunk_text_stamps_uploaded_at():
    chunks = chunk_text("hello world", tenant_id="t1", doc_id="d1", doc_name="a.txt")

    assert chunks[0].uploaded_at is not None
    parsed = datetime.fromisoformat(chunks[0].uploaded_at)
    assert parsed.tzinfo is not None


def test_parses_legacy_payload_without_uploaded_at():
    legacy_payload = {
        "chunk_id": "c1",
        "tenant_id": "t1",
        "doc_id": "d1",
        "doc_name": "doc.txt",
        "chunk_index": 0,
        "text": "hi",
        "content_hash": "abc123",
    }

    chunk = Chunk(**legacy_payload)

    assert chunk.uploaded_at is None
