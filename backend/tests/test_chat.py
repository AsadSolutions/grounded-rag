"""SSE chat endpoint: proves the event order is tokens, then sources, then
trace (CLAUDE.md rule 8 — SSE, never polling), with the compiled graph
swapped for one built from fakes so no real OpenAI/Qdrant call happens.
"""

import app.routers.chat as chat_router
from app.graph.build import build_graph
from app.main import app
from app.models import ChunkGrade, ScoredChunk
from fastapi.testclient import TestClient


def _chunk(chunk_id, text="policy text"):
    return ScoredChunk(
        chunk_id=chunk_id, tenant_id="t1", doc_id="d1", doc_name="handbook.txt", chunk_index=0, text=text, score=1.0
    )


def _parse_sse(raw_text: str) -> list[dict]:
    events = []
    current_event = None
    current_data_lines = []
    for line in raw_text.splitlines():
        if line.startswith("event:"):
            current_event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            current_data_lines.append(line.removeprefix("data:").strip())
        elif line == "" and current_event is not None:
            events.append({"event": current_event, "data": "\n".join(current_data_lines)})
            current_event = None
            current_data_lines = []
    return events


def _wire_fake_graph(monkeypatch, *, generate_fn, check_fn, grade_fn=None):
    graph = build_graph(
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=grade_fn
        or (lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=True, reason="") for c in chunks]),
        generate_fn=generate_fn,
        check_fn=check_fn,
    )
    monkeypatch.setattr(chat_router, "_graph", graph)


def test_chat_streams_tokens_then_sources_then_trace(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "paid time off accrues monthly",
        check_fn=lambda answer, chunks: (True, "fully supported"),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "what is the pto policy"})

    assert response.status_code == 200
    events = _parse_sse(response.text)
    kinds = [e["event"] for e in events]

    assert kinds.count("token") == 5  # "paid time off accrues monthly" -> 5 words
    assert kinds[-2:] == ["sources", "trace"]
    assert all(k == "token" for k in kinds[:-2])


def test_chat_token_events_reconstruct_the_full_answer(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "hello there world",
        check_fn=lambda answer, chunks: (True, "fully supported"),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "hi"})

    events = _parse_sse(response.text)
    import json

    tokens = [json.loads(e["data"])["token"] for e in events if e["event"] == "token"]
    assert "".join(tokens) == "hello there world"


def test_chat_sources_event_contains_only_cited_chunks(monkeypatch):
    graph = build_graph(
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2"), _chunk("c3")],
        grade_fn=lambda question, chunks: [
            ChunkGrade(chunk_id="c1", relevant=True, reason=""),
            ChunkGrade(chunk_id="c2", relevant=False, reason=""),
            ChunkGrade(chunk_id="c3", relevant=True, reason=""),
        ],
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported"),
    )
    monkeypatch.setattr(chat_router, "_graph", graph)
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    sources = json.loads(next(e["data"] for e in events if e["event"] == "sources"))
    assert [s["chunk_id"] for s in sources] == ["c1", "c3"]


def test_chat_trace_event_reports_low_confidence_flag(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (False, "never grounded"),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    trace_payload = json.loads(next(e["data"] for e in events if e["event"] == "trace"))
    assert trace_payload["low_confidence"] is True
    assert any(entry["node"] == "groundedness_check" for entry in trace_payload["entries"])


def test_chat_trace_event_reports_rewrite_count_and_regenerated(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported"),
        grade_fn=lambda question, chunks: [
            ChunkGrade(chunk_id=c.chunk_id, relevant=False, reason="") for c in chunks
        ],
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    trace_payload = json.loads(next(e["data"] for e in events if e["event"] == "trace"))
    assert trace_payload["rewrite_count"] == 2
    assert trace_payload["regenerated"] is False


def test_chat_emits_error_event_instead_of_dying_silently(monkeypatch):
    def _boom(question, chunks, failure_reason=None):
        raise RuntimeError("openai is down")

    _wire_fake_graph(
        monkeypatch,
        generate_fn=_boom,
        check_fn=lambda answer, chunks: (True, "fully supported"),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    assert [e["event"] for e in events] == ["error"]
    assert "openai is down" in json.loads(events[0]["data"])["message"]


def test_chat_rejects_missing_question(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported"),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1"})

    assert response.status_code == 422
