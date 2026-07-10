import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from app.graph.build import build_graph
from app.models import ChatRequest, GraphState

router = APIRouter()

_graph = build_graph()


def _cited_chunks(state: GraphState) -> list:
    relevant_ids = {g.chunk_id for g in state.grades if g.relevant}
    cited = [c for c in state.retrieved_chunks if c.chunk_id in relevant_ids]
    return cited or state.retrieved_chunks


async def _event_stream(request: ChatRequest) -> AsyncIterator[dict]:
    try:
        initial_state = GraphState(question=request.question, tenant_id=request.tenant_id)
        result = GraphState(**await run_in_threadpool(_graph.invoke, initial_state))

        words = result.answer.split(" ") if result.answer else []
        for index, word in enumerate(words):
            token = word if index == len(words) - 1 else f"{word} "
            yield {"event": "token", "data": json.dumps({"token": token})}

        sources = [c.model_dump() for c in _cited_chunks(result)]
        yield {"event": "sources", "data": json.dumps(sources)}

        trace_payload = {
            "low_confidence": result.low_confidence,
            "rewrite_count": result.rewrite_count,
            "regenerated": result.regenerated,
            "entries": [entry.model_dump(exclude_none=True) for entry in result.trace],
        }
        yield {"event": "trace", "data": json.dumps(trace_payload)}
    except Exception as exc:
        yield {"event": "error", "data": json.dumps({"message": str(exc)})}


@router.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    return EventSourceResponse(_event_stream(request))
