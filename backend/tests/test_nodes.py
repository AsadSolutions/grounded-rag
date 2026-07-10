"""Unit tests for every graph node, using fake retrieval/LLM data — never a
real OpenAI or Qdrant call. Each node is a pure function: GraphState in,
GraphState out, with the real LLM/search calls injected as keyword args.
"""

from app.graph.nodes import (
    generate,
    grade,
    groundedness_check,
    retrieve,
    route_after_check,
    route_after_grade,
    rewrite,
)
from app.models import ChunkGrade, GraphState, ScoredChunk


def _chunk(chunk_id, text="some text", score=1.0):
    return ScoredChunk(
        chunk_id=chunk_id, tenant_id="t1", doc_id="d1", doc_name="a.txt", chunk_index=0, text=text, score=score
    )


def _state(**overrides):
    defaults = {"question": "what is the policy", "tenant_id": "t1"}
    defaults.update(overrides)
    return GraphState(**defaults)


# ---- retrieve ----


def test_retrieve_sets_chunks_and_appends_trace():
    fake_chunks = [_chunk("c1"), _chunk("c2")]
    state = _state()

    result = retrieve(state, search_fn=lambda tenant_id, query, k=6: fake_chunks)

    assert result.retrieved_chunks == fake_chunks
    assert len(result.trace) == 1
    assert result.trace[0].node == "retrieve"
    assert result.trace[0].query == "what is the policy"
    assert result.trace[0].chunk_ids == ["c1", "c2"]


def test_retrieve_uses_current_question_and_tenant(monkeypatch):
    seen = {}

    def fake_search(tenant_id, query, k=6):
        seen["tenant_id"] = tenant_id
        seen["query"] = query
        return []

    retrieve(_state(question="q1", tenant_id="tenant-x"), search_fn=fake_search)

    assert seen == {"tenant_id": "tenant-x", "query": "q1"}


# ---- grade ----


def test_grade_sets_grades_and_appends_trace():
    chunks = [_chunk("c1"), _chunk("c2")]
    state = _state(retrieved_chunks=chunks)
    fake_grades = [ChunkGrade(chunk_id="c1", relevant=True, reason="on topic"), ChunkGrade(chunk_id="c2", relevant=False, reason="off topic")]

    result = grade(state, grade_fn=lambda question, chunks: fake_grades)

    assert result.grades == fake_grades
    assert len(result.trace) == 1
    assert result.trace[0].node == "grade"
    assert result.trace[0].grades == fake_grades


# ---- route_after_grade ----


def test_route_after_grade_goes_to_generate_when_enough_relevant_chunks():
    state = _state(grades=[ChunkGrade(chunk_id="c1", relevant=True, reason=""), ChunkGrade(chunk_id="c2", relevant=True, reason="")])

    assert route_after_grade(state) == "generate"


def test_route_after_grade_goes_to_rewrite_when_not_enough_relevant_and_budget_left():
    state = _state(grades=[ChunkGrade(chunk_id="c1", relevant=False, reason="")], rewrite_count=0)

    assert route_after_grade(state) == "rewrite"


def test_route_after_grade_falls_back_to_generate_after_two_rewrites():
    state = _state(grades=[ChunkGrade(chunk_id="c1", relevant=False, reason="")], rewrite_count=2)

    assert route_after_grade(state) == "generate"


def test_route_after_grade_never_allows_a_third_rewrite():
    for rewrite_count in range(5):
        state = _state(grades=[ChunkGrade(chunk_id="c1", relevant=False, reason="")], rewrite_count=rewrite_count)
        decision = route_after_grade(state)
        if rewrite_count < 2:
            assert decision == "rewrite"
        else:
            assert decision == "generate"


# ---- rewrite ----


def test_rewrite_updates_question_and_increments_count_and_appends_trace():
    state = _state(question="pto", rewrite_count=0)

    result = rewrite(state, rewrite_fn=lambda question: "what is the paid time off policy")

    assert result.question == "what is the paid time off policy"
    assert result.rewrite_count == 1
    assert len(result.trace) == 1
    assert result.trace[0].node == "rewrite"
    assert result.trace[0].old_query == "pto"
    assert result.trace[0].new_query == "what is the paid time off policy"


# ---- generate ----


def test_generate_uses_only_relevant_chunks_and_sets_answer():
    chunks = [_chunk("c1", text="relevant text"), _chunk("c2", text="irrelevant text")]
    grades = [ChunkGrade(chunk_id="c1", relevant=True, reason=""), ChunkGrade(chunk_id="c2", relevant=False, reason="")]
    state = _state(retrieved_chunks=chunks, grades=grades)
    seen = {}

    def fake_generate(question, chunks, failure_reason=None):
        seen["chunk_ids"] = [c.chunk_id for c in chunks]
        seen["failure_reason"] = failure_reason
        return "the answer"

    result = generate(state, generate_fn=fake_generate)

    assert result.answer == "the answer"
    assert seen["chunk_ids"] == ["c1"]
    assert seen["failure_reason"] is None
    assert len(result.trace) == 1
    assert result.trace[0].node == "generate"
    assert result.trace[0].is_regeneration is False


def test_generate_flags_low_confidence_when_fewer_than_two_relevant_chunks():
    chunks = [_chunk("c1")]
    grades = [ChunkGrade(chunk_id="c1", relevant=False, reason="")]
    state = _state(retrieved_chunks=chunks, grades=grades)

    result = generate(state, generate_fn=lambda question, chunks, failure_reason=None: "best effort answer")

    assert result.low_confidence is True
    # Falls back to using whatever was retrieved when nothing graded relevant.
    assert result.answer == "best effort answer"


def test_generate_does_not_flag_low_confidence_with_enough_relevant_chunks():
    chunks = [_chunk("c1"), _chunk("c2")]
    grades = [ChunkGrade(chunk_id="c1", relevant=True, reason=""), ChunkGrade(chunk_id="c2", relevant=True, reason="")]
    state = _state(retrieved_chunks=chunks, grades=grades)

    result = generate(state, generate_fn=lambda question, chunks, failure_reason=None: "answer")

    assert result.low_confidence is False


def test_generate_marks_regenerated_when_called_with_a_failure_reason():
    chunks = [_chunk("c1"), _chunk("c2")]
    grades = [ChunkGrade(chunk_id="c1", relevant=True, reason=""), ChunkGrade(chunk_id="c2", relevant=True, reason="")]
    state = _state(
        retrieved_chunks=chunks,
        grades=grades,
        answer="first attempt",
        groundedness_failure_reason="claimed a fact not in the sources",
    )

    result = generate(state, generate_fn=lambda question, chunks, failure_reason=None: "second attempt")

    assert result.answer == "second attempt"
    assert result.regenerated is True
    assert result.trace[0].is_regeneration is True


# ---- groundedness_check ----


def test_groundedness_check_records_grounded_verdict():
    state = _state(answer="the policy is X", retrieved_chunks=[_chunk("c1")], grades=[ChunkGrade(chunk_id="c1", relevant=True, reason="")])

    result = groundedness_check(state, check_fn=lambda answer, chunks: (True, "fully supported", []))

    assert result.groundedness is True
    assert result.groundedness_failure_reason is None
    assert len(result.trace) == 1
    assert result.trace[0].node == "groundedness_check"
    assert result.trace[0].grounded is True
    assert result.trace[0].unsupported_claims == []


def test_groundedness_check_records_failure_reason_when_not_grounded():
    state = _state(answer="the policy is X", retrieved_chunks=[_chunk("c1")], grades=[ChunkGrade(chunk_id="c1", relevant=True, reason="")])

    result = groundedness_check(
        state,
        check_fn=lambda answer, chunks: (
            False,
            "claims a number not present in sources",
            ["claims a number not present in sources"],
        ),
    )

    assert result.groundedness is False
    assert result.groundedness_failure_reason == "claims a number not present in sources"
    assert result.trace[0].grounded is False
    assert result.trace[0].unsupported_claims == ["claims a number not present in sources"]


def test_groundedness_check_sets_low_confidence_when_exhausted_after_regeneration():
    state = _state(answer="answer", retrieved_chunks=[_chunk("c1")], regenerated=True)

    result = groundedness_check(state, check_fn=lambda answer, chunks: (False, "still not grounded", ["still not grounded"]))

    assert result.low_confidence is True


def test_groundedness_check_does_not_flag_low_confidence_on_first_failure():
    state = _state(answer="answer", retrieved_chunks=[_chunk("c1")], regenerated=False)

    result = groundedness_check(state, check_fn=lambda answer, chunks: (False, "not grounded yet", ["not grounded yet"]))

    assert result.low_confidence is False


# ---- route_after_check ----


def test_route_after_check_finishes_when_grounded():
    state = _state(groundedness=True)

    assert route_after_check(state) == "finish"


def test_route_after_check_regenerates_once_when_not_grounded():
    state = _state(groundedness=False, regenerated=False)

    assert route_after_check(state) == "regenerate"


def test_route_after_check_never_regenerates_twice():
    state = _state(groundedness=False, regenerated=True)

    assert route_after_check(state) == "finish_low_confidence"
