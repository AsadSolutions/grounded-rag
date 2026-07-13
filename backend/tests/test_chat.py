"""SSE chat endpoint: proves the event order is tokens, then sources, then
trace (CLAUDE.md rule 8 — SSE, never polling), with the compiled graph
swapped for one built from fakes so no real OpenAI/Qdrant call happens.
"""

import logging

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


def _wire_fake_graph(monkeypatch, *, generate_fn, check_fn, grade_fn=None, rewrite_fn=None):
    graph = build_graph(
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=grade_fn
        or (lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=True, reason="") for c in chunks]),
        rewrite_fn=rewrite_fn or (lambda question: f"{question} (rewritten)"),
        generate_fn=generate_fn,
        check_fn=check_fn,
    )
    monkeypatch.setattr(chat_router, "_graph", graph)
    # Placeholder test questions ("q", "hi") would otherwise fall through to
    # classify_intent's real LLM fallback, since only smalltalk/document_meta
    # have fast-path regexes. Force every graph-path test onto the graph
    # deterministically, with no real OpenAI call.
    monkeypatch.setattr(chat_router, "classify_intent", lambda question: "document_question")


def test_chat_streams_stages_then_tokens_then_sources_then_trace(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "paid time off accrues monthly",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "what is the pto policy"})

    assert response.status_code == 200
    events = _parse_sse(response.text)
    kinds = [e["event"] for e in events]

    # retrieve, grade, generate, groundedness_check — no rewrite, since the
    # default grade_fn in _wire_fake_graph marks every chunk relevant.
    assert kinds[:4] == ["stage", "stage", "stage", "stage"]
    assert kinds.count("token") == 5  # "paid time off accrues monthly" -> 5 words
    assert kinds[-2:] == ["sources", "trace"]
    assert all(k == "token" for k in kinds[4:-2])


def test_chat_stage_events_report_human_readable_node_labels(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    labels = [json.loads(e["data"])["label"] for e in events if e["event"] == "stage"]

    assert labels == [
        "Searching documents",
        "Checking relevance",
        "Writing answer",
        "Verifying answer",
    ]


def test_chat_stage_events_include_refining_search_on_rewrite(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
        grade_fn=lambda question, chunks: [
            ChunkGrade(chunk_id=c.chunk_id, relevant=False, reason="") for c in chunks
        ],
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    labels = [json.loads(e["data"])["label"] for e in events if e["event"] == "stage"]

    assert labels.count("Refining search") == 2  # MAX_REWRITES


def test_chat_token_events_reconstruct_the_full_answer(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "hello there world",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
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
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    monkeypatch.setattr(chat_router, "_graph", graph)
    monkeypatch.setattr(chat_router, "classify_intent", lambda question: "document_question")
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
        check_fn=lambda answer, chunks: (False, "never grounded", ["never grounded"]),
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
        check_fn=lambda answer, chunks: (True, "fully supported", []),
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


def test_chat_trace_entries_carry_structured_fields_and_omit_unused_ones(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    trace_payload = json.loads(next(e["data"] for e in events if e["event"] == "trace"))
    entries_by_node = {entry["node"]: entry for entry in trace_payload["entries"]}

    retrieve_entry = entries_by_node["retrieve"]
    assert retrieve_entry["chunk_ids"] == ["c1", "c2"]
    assert "grades" not in retrieve_entry

    grade_entry = entries_by_node["grade"]
    assert [g["chunk_id"] for g in grade_entry["grades"]] == ["c1", "c2"]
    assert "chunk_ids" not in grade_entry

    groundedness_entry = entries_by_node["groundedness_check"]
    assert groundedness_entry["grounded"] is True
    assert groundedness_entry["unsupported_claims"] == []


def test_chat_emits_error_event_instead_of_dying_silently(monkeypatch, caplog):
    def _boom(question, chunks, failure_reason=None):
        raise RuntimeError("openai is down")

    _wire_fake_graph(
        monkeypatch,
        generate_fn=_boom,
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    api = TestClient(app)

    with caplog.at_level(logging.ERROR):
        response = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    import json

    events = _parse_sse(response.text)
    kinds = [e["event"] for e in events]
    # retrieve and grade complete (and emit their stage events) before
    # generate raises — the failure still ends the stream with a single
    # error event, just after whatever real progress happened first.
    assert kinds[-1] == "error"
    assert all(k == "stage" for k in kinds[:-1])

    message = json.loads(events[-1]["data"])["message"]
    # Clean to the client: no internal exception text leaks over the wire.
    assert "openai is down" not in message
    assert message == "Something went wrong answering your question. Please try again."
    # Loud on the server: the real cause is logged, not swallowed.
    assert "openai is down" in caplog.text


def test_chat_returns_429_after_exceeding_the_rate_limit(monkeypatch):
    import app.routers.chat as chat_module
    from app.rate_limit import RateLimiter

    monkeypatch.setattr(chat_module, "_chat_rate_limiter", RateLimiter(max_requests=1, window_seconds=60))
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    api = TestClient(app)

    first = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})
    second = api.post("/api/chat", json={"tenant_id": "t1", "question": "q"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_chat_rejects_missing_question(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1"})

    assert response.status_code == 422


def test_chat_smalltalk_bypasses_the_graph_entirely(monkeypatch):
    class _ExplodingGraph:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("graph should not run for smalltalk")

        def stream(self, *args, **kwargs):
            raise RuntimeError("graph should not run for smalltalk")

    monkeypatch.setattr(chat_router, "_graph", _ExplodingGraph())
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "hello"})

    assert response.status_code == 200
    events = _parse_sse(response.text)
    kinds = [e["event"] for e in events]
    assert kinds[-2:] == ["sources", "trace"]
    assert all(k == "token" for k in kinds[:-2])

    import json

    trace_payload = json.loads(next(e["data"] for e in events if e["event"] == "trace"))
    assert trace_payload["skipped_pipeline"] is True
    sources = json.loads(next(e["data"] for e in events if e["event"] == "sources"))
    assert sources == []


def test_chat_document_meta_bypasses_the_graph_and_lists_documents(monkeypatch):
    class _ExplodingGraph:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("graph should not run for document_meta")

        def stream(self, *args, **kwargs):
            raise RuntimeError("graph should not run for document_meta")

    monkeypatch.setattr(chat_router, "_graph", _ExplodingGraph())
    monkeypatch.setattr(
        chat_router,
        "answer_document_meta",
        lambda tenant_id: "You have 2 documents:\n- a.txt\n- b.txt",
    )
    api = TestClient(app)

    response = api.post(
        "/api/chat", json={"tenant_id": "t1", "question": "how many documents do you have?"}
    )

    import json

    events = _parse_sse(response.text)
    tokens = [json.loads(e["data"])["token"] for e in events if e["event"] == "token"]
    assert "".join(tokens) == "You have 2 documents:\n- a.txt\n- b.txt"
    trace_payload = json.loads(next(e["data"] for e in events if e["event"] == "trace"))
    assert trace_payload["skipped_pipeline"] is True


def test_chat_regular_question_still_runs_the_graph_and_marks_skipped_pipeline_false(monkeypatch):
    _wire_fake_graph(
        monkeypatch,
        generate_fn=lambda question, chunks, failure_reason=None: "paid time off accrues monthly",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )
    api = TestClient(app)

    response = api.post("/api/chat", json={"tenant_id": "t1", "question": "what is the pto policy"})

    import json

    trace_payload = json.loads(
        next(e["data"] for e in _parse_sse(response.text) if e["event"] == "trace")
    )
    assert trace_payload["skipped_pipeline"] is False
