"""Graph nodes: pure functions of GraphState.

The real OpenAI/search calls are injected as keyword-only args with real
defaults, so nodes are directly unit-testable with fake data and
app.graph.build wires the real implementations together for production.
"""

from pydantic import BaseModel

from app.config import get_settings
from app.models import ChunkGrade, GraphState, ScoredChunk, TraceEntry
from app.retrieval.hybrid import hybrid_search

MIN_RELEVANT_CHUNKS = 2
MAX_REWRITES = 2


def _openai_client():
    from openai import OpenAI

    return OpenAI(api_key=get_settings().openai_api_key)


class _GradeList(BaseModel):
    grades: list[ChunkGrade]


def grade_chunks_llm(question: str, chunks: list[ScoredChunk]) -> list[ChunkGrade]:
    if not chunks:
        return []
    settings = get_settings()
    chunk_listing = "\n\n".join(f"chunk_id: {c.chunk_id}\n{c.text}" for c in chunks)
    response = _openai_client().chat.completions.parse(
        model=settings.chat_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Grade each chunk relevant or not relevant to the question. "
                    "Return exactly one grade per chunk_id given."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nChunks:\n{chunk_listing}"},
        ],
        response_format=_GradeList,
    )
    return response.choices[0].message.parsed.grades


def rewrite_query_llm(question: str) -> str:
    settings = get_settings()
    response = _openai_client().chat.completions.create(
        model=settings.chat_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Rewrite the question to be more retrievable: expand abbreviations, "
                    "add likely synonyms. Return only the rewritten question."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_answer_llm(question: str, chunks: list[ScoredChunk], failure_reason: str | None = None) -> str:
    settings = get_settings()
    sources = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in chunks)
    instructions = (
        "Answer strictly from the sources below, citing chunk ids in brackets. "
        'If the sources do not contain the answer, say "not found in the documents" '
        "instead of guessing."
    )
    if failure_reason:
        instructions += f" Your previous attempt failed a groundedness check: {failure_reason}. Fix this."
    response = _openai_client().chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"Question: {question}\n\nSources:\n{sources}"},
        ],
    )
    return response.choices[0].message.content.strip()


class _GroundednessExtraction(BaseModel):
    unsupported_claims: list[str]


def check_groundedness_llm(answer: str, chunks: list[ScoredChunk]) -> tuple[bool, str]:
    """Returns (grounded, reason). `grounded` is derived in code from whether the model's
    unsupported_claims list is empty, rather than asked of the model directly — an earlier
    version had the model produce grounded as its own field and it periodically contradicted
    its own claims list (grounded=false with an empty list, or vice versa) because structured
    output decodes JSON fields in schema order, forcing a verdict before the claim-by-claim
    extraction that was supposed to justify it. See app/eval/judge.py for the same fix.

    `reason` lists the unsupported claims verbatim when not grounded, so the regeneration
    prompt in generate_answer_llm's failure_reason sees exactly what failed, not a vague
    restatement.
    """
    settings = get_settings()
    sources = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in chunks)
    response = _openai_client().chat.completions.parse(
        model=settings.chat_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract every discrete factual claim the answer makes, then check each "
                    "claim against the sources one at a time, judging the meaning of the claim "
                    "against the meaning of the sources, not the exact wording. A claim is "
                    "SUPPORTED if it is a faithful paraphrase, rewording, summary, or unit "
                    "conversion of something the sources state, or if it resolves a pronoun or "
                    "reference to an entity the sources name in the same context — combining "
                    "several sentences from the sources into one is not a fabrication. A claim "
                    "is UNSUPPORTED only if it introduces a specific fact, number, entity, "
                    "exception, or condition that the sources do not state and cannot be "
                    "reasonably derived from what they do state. List every unsupported claim "
                    "verbatim in unsupported_claims; leave it empty if every claim is supported. "
                    'An answer that says the information was "not found in the documents", and '
                    "makes no other factual claims, has no unsupported claims."
                ),
            },
            {"role": "user", "content": f"Answer: {answer}\n\nSources:\n{sources}"},
        ],
        response_format=_GroundednessExtraction,
    )
    extraction = response.choices[0].message.parsed
    grounded = len(extraction.unsupported_claims) == 0
    reason = "Fully supported." if grounded else "Unsupported claims: " + "; ".join(extraction.unsupported_claims)
    return grounded, reason


def retrieve(state: GraphState, *, search_fn=hybrid_search) -> GraphState:
    chunks = search_fn(state.tenant_id, state.question, k=6)
    trace_entry = TraceEntry(node="retrieve", message=f"Retrieved {len(chunks)} chunk(s) for: {state.question!r}")
    return state.model_copy(update={"retrieved_chunks": chunks, "trace": [*state.trace, trace_entry]})


def grade(state: GraphState, *, grade_fn=grade_chunks_llm) -> GraphState:
    grades = grade_fn(state.question, state.retrieved_chunks)
    relevant_count = sum(1 for g in grades if g.relevant)
    trace_entry = TraceEntry(node="grade", message=f"Graded {len(grades)} chunk(s): {relevant_count} relevant")
    return state.model_copy(update={"grades": grades, "trace": [*state.trace, trace_entry]})


def route_after_grade(state: GraphState) -> str:
    relevant_count = sum(1 for g in state.grades if g.relevant)
    if relevant_count >= MIN_RELEVANT_CHUNKS:
        return "generate"
    if state.rewrite_count < MAX_REWRITES:
        return "rewrite"
    return "generate"


def rewrite(state: GraphState, *, rewrite_fn=rewrite_query_llm) -> GraphState:
    new_question = rewrite_fn(state.question)
    trace_entry = TraceEntry(node="rewrite", message=f"Rewrote question to: {new_question!r}")
    return state.model_copy(
        update={
            "question": new_question,
            "rewrite_count": state.rewrite_count + 1,
            "trace": [*state.trace, trace_entry],
        }
    )


def _relevant_chunks(state: GraphState) -> tuple[list[ScoredChunk], bool]:
    relevant_ids = {g.chunk_id for g in state.grades if g.relevant}
    relevant = [c for c in state.retrieved_chunks if c.chunk_id in relevant_ids]
    low_confidence = len(relevant) < MIN_RELEVANT_CHUNKS
    if not relevant:
        relevant = state.retrieved_chunks
    return relevant, low_confidence


def generate(state: GraphState, *, generate_fn=generate_answer_llm) -> GraphState:
    relevant, retrieval_low_confidence = _relevant_chunks(state)
    answer = generate_fn(state.question, relevant, failure_reason=state.groundedness_failure_reason)
    is_regeneration = state.groundedness_failure_reason is not None
    message = "Generated answer" + (" after regeneration" if is_regeneration else "")
    trace_entry = TraceEntry(node="generate", message=message)
    return state.model_copy(
        update={
            "answer": answer,
            "low_confidence": state.low_confidence or retrieval_low_confidence,
            "regenerated": state.regenerated or is_regeneration,
            "trace": [*state.trace, trace_entry],
        }
    )


def groundedness_check(state: GraphState, *, check_fn=check_groundedness_llm) -> GraphState:
    relevant, _ = _relevant_chunks(state)
    grounded, reason = check_fn(state.answer, relevant)
    exhausted_regeneration = state.regenerated
    trace_entry = TraceEntry(
        node="groundedness_check", message=f"{'Grounded' if grounded else 'NOT grounded'}: {reason}"
    )
    return state.model_copy(
        update={
            "groundedness": grounded,
            "groundedness_failure_reason": None if grounded else reason,
            "low_confidence": state.low_confidence or (not grounded and exhausted_regeneration),
            "trace": [*state.trace, trace_entry],
        }
    )


def route_after_check(state: GraphState) -> str:
    if state.groundedness:
        return "finish"
    if not state.regenerated:
        return "regenerate"
    return "finish_low_confidence"
