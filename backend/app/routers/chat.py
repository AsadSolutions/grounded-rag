import asyncio
import json
import logging
import queue
import threading
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.chat_intent import answer_document_meta, answer_smalltalk, classify_intent
from app.config import get_settings
from app.graph.build import build_graph
from app.models import ChatRequest, GraphState, TraceEntry
from app.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter()

_graph = build_graph()
_chat_rate_limiter = RateLimiter(
    max_requests=get_settings().chat_rate_limit_per_minute, window_seconds=60
)

_SENTINEL = object()

_STAGE_LABELS = {
    "retrieve": "Searching documents",
    "grade": "Checking relevance",
    "rewrite": "Refining search",
    "groundedness_check": "Verifying answer",
}


def _stage_label(trace_entry: TraceEntry) -> str:
    if trace_entry.node == "generate":
        return "Rewriting answer" if trace_entry.is_regeneration else "Writing answer"
    return _STAGE_LABELS.get(trace_entry.node, trace_entry.node)


async def _stream_graph_states(graph, initial_state: GraphState) -> AsyncIterator[GraphState]:
    """Runs graph.stream() on a worker thread — node functions make blocking
    OpenAI/Qdrant calls — and bridges each intermediate state back onto the
    event loop via a queue, so the SSE generator can emit progress before
    the graph finishes instead of only after invoke() returns."""
    state_queue: queue.Queue = queue.Queue()
    loop = asyncio.get_event_loop()

    def _run() -> None:
        try:
            for raw_state in graph.stream(initial_state, stream_mode="values"):
                state_queue.put(GraphState(**raw_state))
        except Exception as exc:  # re-raised on the consumer side, not swallowed
            state_queue.put(exc)
        finally:
            state_queue.put(_SENTINEL)

    threading.Thread(target=_run, daemon=True).start()

    while True:
        item = await loop.run_in_executor(None, state_queue.get)
        if item is _SENTINEL:
            return
        if isinstance(item, Exception):
            raise item
        yield item


def _check_chat_rate_limit(request: Request) -> None:
    # Indirection (rather than `Depends(_chat_rate_limiter)` directly) so
    # tests can monkeypatch the module-level `_chat_rate_limiter` name and
    # have it take effect: FastAPI resolves a Depends() target once, at
    # route-definition time, so binding the object itself as the default
    # would freeze in the original instance forever.
    _chat_rate_limiter(request)


def _cited_chunks(state: GraphState) -> list:
    relevant_ids = {g.chunk_id for g in state.grades if g.relevant}
    cited = [c for c in state.retrieved_chunks if c.chunk_id in relevant_ids]
    return cited or state.retrieved_chunks


def _tokenize(answer: str) -> list[str]:
    words = answer.split(" ") if answer else []
    return [word if index == len(words) - 1 else f"{word} " for index, word in enumerate(words)]


def _bypass_answer(intent: str, request: ChatRequest) -> str:
    if intent == "smalltalk":
        return answer_smalltalk(request.question)
    return answer_document_meta(request.tenant_id)


async def _event_stream(request: ChatRequest) -> AsyncIterator[dict]:
    try:
        intent = classify_intent(request.question)
        if intent in ("smalltalk", "document_meta"):
            answer = _bypass_answer(intent, request)
            for token in _tokenize(answer):
                yield {"event": "token", "data": json.dumps({"token": token})}

            yield {"event": "sources", "data": json.dumps([])}

            trace_payload = {
                "low_confidence": False,
                "rewrite_count": 0,
                "regenerated": False,
                "skipped_pipeline": True,
                "entries": [TraceEntry(node=intent, message=answer).model_dump(exclude_none=True)],
            }
            yield {"event": "trace", "data": json.dumps(trace_payload)}
            return

        initial_state = GraphState(question=request.question, tenant_id=request.tenant_id)
        result = initial_state
        seen_trace_len = 0
        async for state in _stream_graph_states(_graph, initial_state):
            result = state
            if len(state.trace) > seen_trace_len:
                seen_trace_len = len(state.trace)
                yield {"event": "stage", "data": json.dumps({"label": _stage_label(state.trace[-1])})}

        for token in _tokenize(result.answer):
            yield {"event": "token", "data": json.dumps({"token": token})}

        sources = [c.model_dump() for c in _cited_chunks(result)]
        yield {"event": "sources", "data": json.dumps(sources)}

        trace_payload = {
            "low_confidence": result.low_confidence,
            "rewrite_count": result.rewrite_count,
            "regenerated": result.regenerated,
            "skipped_pipeline": False,
            "entries": [entry.model_dump(exclude_none=True) for entry in result.trace],
        }
        yield {"event": "trace", "data": json.dumps(trace_payload)}
    except Exception:
        logger.exception("Chat pipeline failed for tenant_id=%s", request.tenant_id)
        yield {
            "event": "error",
            "data": json.dumps(
                {"message": "Something went wrong answering your question. Please try again."}
            ),
        }


@router.post("/api/chat")
async def chat(
    request: ChatRequest, _: None = Depends(_check_chat_rate_limit)
) -> EventSourceResponse:
    return EventSourceResponse(_event_stream(request))
