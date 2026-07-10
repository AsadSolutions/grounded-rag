"""Integration tests for the compiled graph: real control flow (loops,
routing, state threading) exercised end-to-end, with fake search/LLM
functions injected. This is what proves the hard limits in CLAUDE.md rule 7
actually terminate the loops, and mirrors the Phase 2 exit check scenario
(a vague question that needs a rewrite, watched via the trace).
"""

from app.graph.build import build_graph
from app.models import ChunkGrade, GraphState, ScoredChunk


def _chunk(chunk_id):
    return ScoredChunk(
        chunk_id=chunk_id, tenant_id="t1", doc_id="d1", doc_name="a.txt", chunk_index=0, text="text", score=1.0
    )


def _run(state, **fns):
    graph = build_graph(**fns)
    result = graph.invoke(state)
    return GraphState(**result)


def test_graph_answers_directly_when_retrieval_is_immediately_good():
    state = GraphState(question="what is the travel policy", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=True, reason="") for c in chunks],
        generate_fn=lambda question, chunks, failure_reason=None: "the answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )

    assert result.answer == "the answer"
    assert result.rewrite_count == 0
    assert result.regenerated is False
    assert result.low_confidence is False
    assert [t.node for t in result.trace] == ["retrieve", "grade", "generate", "groundedness_check"]


def test_graph_rewrites_once_then_succeeds():
    grade_calls = {"count": 0}

    def fake_grade(question, chunks):
        grade_calls["count"] += 1
        relevant = grade_calls["count"] >= 2
        return [ChunkGrade(chunk_id=c.chunk_id, relevant=relevant, reason="") for c in chunks]

    state = GraphState(question="pto?", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=fake_grade,
        rewrite_fn=lambda question: "what is the paid time off policy",
        generate_fn=lambda question, chunks, failure_reason=None: "the answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )

    assert result.rewrite_count == 1
    assert result.question == "what is the paid time off policy"
    assert result.low_confidence is False
    assert [t.node for t in result.trace] == [
        "retrieve",
        "grade",
        "rewrite",
        "retrieve",
        "grade",
        "generate",
        "groundedness_check",
    ]


def test_graph_trace_carries_per_chunk_grades_and_both_queries_on_rewrite_path():
    grade_calls = {"count": 0}

    def fake_grade(question, chunks):
        grade_calls["count"] += 1
        relevant = grade_calls["count"] >= 2
        return [ChunkGrade(chunk_id=c.chunk_id, relevant=relevant, reason="") for c in chunks]

    state = GraphState(question="pto?", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=fake_grade,
        rewrite_fn=lambda question: "what is the paid time off policy",
        generate_fn=lambda question, chunks, failure_reason=None: "the answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )

    grade_entries = [t for t in result.trace if t.node == "grade"]
    assert len(grade_entries) == 2
    for entry in grade_entries:
        assert [g.chunk_id for g in entry.grades] == ["c1", "c2"]
    assert grade_entries[0].grades[0].relevant is False
    assert grade_entries[1].grades[0].relevant is True

    rewrite_entry = next(t for t in result.trace if t.node == "rewrite")
    assert rewrite_entry.old_query == "pto?"
    assert rewrite_entry.new_query == "what is the paid time off policy"

    groundedness_entry = next(t for t in result.trace if t.node == "groundedness_check")
    assert groundedness_entry.grounded is True
    assert groundedness_entry.unsupported_claims == []


def test_graph_never_exceeds_two_rewrites_and_still_finishes():
    state = GraphState(question="vague", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1")],
        grade_fn=lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=False, reason="") for c in chunks],
        rewrite_fn=lambda question: question + "!",
        generate_fn=lambda question, chunks, failure_reason=None: "best effort",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )

    assert result.rewrite_count == 2
    assert result.low_confidence is True
    assert result.answer == "best effort"
    rewrite_count_in_trace = sum(1 for t in result.trace if t.node == "rewrite")
    assert rewrite_count_in_trace == 2


def test_graph_regenerates_once_then_succeeds():
    check_calls = {"count": 0}

    def fake_check(answer, chunks):
        check_calls["count"] += 1
        if check_calls["count"] == 1:
            return False, "claimed a fact not in the sources", ["claimed a fact not in the sources"]
        return True, "fully supported", []

    state = GraphState(question="what is the policy", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=True, reason="") for c in chunks],
        generate_fn=lambda question, chunks, failure_reason=None: "corrected answer" if failure_reason else "first answer",
        check_fn=fake_check,
    )

    assert result.regenerated is True
    assert result.groundedness is True
    assert result.answer == "corrected answer"
    assert result.low_confidence is False
    generate_count_in_trace = sum(1 for t in result.trace if t.node == "generate")
    assert generate_count_in_trace == 2


def test_graph_never_regenerates_twice_and_finishes_low_confidence():
    state = GraphState(question="what is the policy", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=True, reason="") for c in chunks],
        generate_fn=lambda question, chunks, failure_reason=None: "an answer",
        check_fn=lambda answer, chunks: (False, "never grounded", ["never grounded"]),
    )

    assert result.regenerated is True
    assert result.groundedness is False
    assert result.low_confidence is True
    generate_count_in_trace = sum(1 for t in result.trace if t.node == "generate")
    check_count_in_trace = sum(1 for t in result.trace if t.node == "groundedness_check")
    assert generate_count_in_trace == 2
    assert check_count_in_trace == 2


def test_build_graph_with_correction_disabled_skips_grade_rewrite_and_groundedness():
    state = GraphState(question="what is the travel policy", tenant_id="t1")

    result = _run(
        state,
        correction_enabled=False,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        generate_fn=lambda question, chunks, failure_reason=None: "the answer",
    )

    assert result.answer == "the answer"
    assert [t.node for t in result.trace] == ["retrieve", "generate"]
    assert result.grades == []
    assert result.groundedness is None
    assert result.rewrite_count == 0
    assert result.regenerated is False


def test_build_graph_correction_enabled_defaults_to_true_and_is_unchanged():
    state = GraphState(question="what is the travel policy", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1"), _chunk("c2")],
        grade_fn=lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=True, reason="") for c in chunks],
        generate_fn=lambda question, chunks, failure_reason=None: "the answer",
        check_fn=lambda answer, chunks: (True, "fully supported", []),
    )

    assert [t.node for t in result.trace] == ["retrieve", "grade", "generate", "groundedness_check"]


def test_graph_terminates_in_worst_case_of_both_hard_limits():
    state = GraphState(question="vague", tenant_id="t1")

    result = _run(
        state,
        search_fn=lambda tenant_id, query, k=6: [_chunk("c1")],
        grade_fn=lambda question, chunks: [ChunkGrade(chunk_id=c.chunk_id, relevant=False, reason="") for c in chunks],
        rewrite_fn=lambda question: question + "!",
        generate_fn=lambda question, chunks, failure_reason=None: "best effort",
        check_fn=lambda answer, chunks: (False, "never grounded", ["never grounded"]),
    )

    assert result.rewrite_count == 2
    assert result.regenerated is True
    assert result.low_confidence is True
