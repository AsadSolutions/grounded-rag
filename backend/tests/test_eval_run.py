from app.eval.run import (
    build_question_transcript,
    judge_agreement_count,
    matches_expected_chunk,
    render_category_breakdown_md,
    render_results_md,
    run_question,
    said_not_found,
    summarize,
    summarize_by_category,
)
from app.eval.schemas import ExpectedChunk, GoldenQuestion, JudgeVerdict, QuestionOutcome, RunSummary
from app.models import ChunkGrade, GraphState, ScoredChunk, TraceEntry


def _chunk(doc_name, text, chunk_id="c1"):
    return ScoredChunk(
        chunk_id=chunk_id, tenant_id="t1", doc_id="d1", doc_name=doc_name, chunk_index=0, text=text, score=1.0
    )


def _question(**overrides):
    defaults = dict(
        id="q1",
        tenant_id="t1",
        question="what is x",
        expected_answer_facts=["x"],
        expected_chunks=[ExpectedChunk(doc_name="a.md", contains="the answer is x")],
        unanswerable=False,
    )
    defaults.update(overrides)
    return GoldenQuestion(**defaults)


class _FakeGraph:
    def __init__(self, retrieved_chunks, answer):
        self._retrieved_chunks = retrieved_chunks
        self._answer = answer

    def invoke(self, state):
        return {
            **state.model_dump(),
            "retrieved_chunks": [c.model_dump() for c in self._retrieved_chunks],
            "answer": self._answer,
        }


# ---- matches_expected_chunk ----


def test_matches_expected_chunk_true_when_doc_and_substring_present():
    question = _question()
    chunks = [_chunk("a.md", "some prose. the answer is x. more prose.")]

    assert matches_expected_chunk(chunks, question) is True


def test_matches_expected_chunk_false_when_doc_matches_but_substring_missing():
    question = _question()
    chunks = [_chunk("a.md", "unrelated text")]

    assert matches_expected_chunk(chunks, question) is False


def test_matches_expected_chunk_false_when_substring_in_wrong_doc():
    question = _question()
    chunks = [_chunk("b.md", "the answer is x")]

    assert matches_expected_chunk(chunks, question) is False


def test_matches_expected_chunk_is_case_insensitive():
    question = _question()
    chunks = [_chunk("a.md", "THE ANSWER IS X")]

    assert matches_expected_chunk(chunks, question) is True


# ---- said_not_found ----


def test_said_not_found_detects_the_refusal_phrase():
    assert said_not_found("Not found in the documents.") is True
    assert said_not_found("NOT FOUND IN THE DOCUMENTS, sorry.") is True


def test_said_not_found_false_for_a_confident_answer():
    assert said_not_found("The rate is $475 per hour.") is False


# ---- run_question ----


def test_run_question_computes_retrieval_hit_and_grounded_for_an_answerable_question():
    question = _question()
    graph = _FakeGraph([_chunk("a.md", "the answer is x")], "x is the answer [c1]")

    outcome = run_question(
        question, graph, judge_fn=lambda q, a, c: JudgeVerdict(grounded=True, unsupported_claims=[], reason="ok")
    )

    assert outcome.retrieval_hit is True
    assert outcome.grounded is True
    assert outcome.honest_refusal is None
    assert outcome.category == "baseline"


def test_run_question_scores_honesty_only_for_unanswerable_questions():
    question = _question(unanswerable=True, expected_answer_facts=[], expected_chunks=[])
    graph = _FakeGraph([_chunk("a.md", "irrelevant")], "Not found in the documents.")

    outcome = run_question(
        question,
        graph,
        judge_fn=lambda q, a, c: JudgeVerdict(grounded=True, unsupported_claims=[], reason="honest refusal"),
    )

    assert outcome.retrieval_hit is None
    assert outcome.honest_refusal is True


def test_run_question_does_not_flag_honesty_for_answerable_questions():
    question = _question()
    graph = _FakeGraph([_chunk("a.md", "the answer is x")], "x is the answer [c1]")

    outcome = run_question(
        question, graph, judge_fn=lambda q, a, c: JudgeVerdict(grounded=True, unsupported_claims=[], reason="ok")
    )

    assert outcome.honest_refusal is None


class _FakeGraphWithInternalVerdict(_FakeGraph):
    def __init__(self, retrieved_chunks, answer, internal_groundedness):
        super().__init__(retrieved_chunks, answer)
        self._internal_groundedness = internal_groundedness

    def invoke(self, state):
        return {**super().invoke(state), "groundedness": self._internal_groundedness}


def test_run_question_captures_the_pipelines_internal_groundedness_verdict():
    question = _question()
    graph = _FakeGraphWithInternalVerdict([_chunk("a.md", "the answer is x")], "x is the answer [c1]", True)

    outcome = run_question(
        question, graph, judge_fn=lambda q, a, c: JudgeVerdict(grounded=False, unsupported_claims=["x"], reason="no")
    )

    assert outcome.internal_groundedness is True
    assert outcome.grounded is False


def test_run_question_internal_groundedness_is_none_when_correction_is_off():
    question = _question()
    graph = _FakeGraph([_chunk("a.md", "the answer is x")], "x is the answer [c1]")

    outcome = run_question(
        question, graph, judge_fn=lambda q, a, c: JudgeVerdict(grounded=True, unsupported_claims=[], reason="ok")
    )

    assert outcome.internal_groundedness is None


# ---- judge_agreement_count ----


def test_judge_agreement_count_counts_matches_among_comparable_outcomes():
    outcomes = [
        QuestionOutcome(
            question_id="a", tenant_id="t1", category="baseline", retrieval_hit=True, grounded=True,
            internal_groundedness=True, honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="b", tenant_id="t1", category="baseline", retrieval_hit=True, grounded=False,
            internal_groundedness=True, honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="c", tenant_id="t1", category="baseline", retrieval_hit=True, grounded=False,
            internal_groundedness=None, honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
    ]

    agreements, comparable = judge_agreement_count(outcomes)

    assert comparable == 2
    assert agreements == 1


# ---- summarize ----


def test_summarize_computes_rates_across_answerable_and_unanswerable_questions():
    outcomes = [
        QuestionOutcome(
            question_id="a", tenant_id="t1", category="baseline", retrieval_hit=True, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="b", tenant_id="t1", category="baseline", retrieval_hit=False, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="c", tenant_id="t1", category="baseline", retrieval_hit=None, grounded=True, internal_groundedness=None,
            honest_refusal=True, answer="", rewrite_count=0, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="d", tenant_id="t1", category="baseline", retrieval_hit=None, grounded=False, internal_groundedness=None,
            honest_refusal=False, answer="", rewrite_count=0, low_confidence=False,
        ),
    ]

    summary = summarize("correction_on", outcomes)

    assert summary.n_questions == 4
    assert summary.retrieval_hit_rate == 0.5
    assert summary.groundedness_rate == 0.75
    assert summary.not_found_honesty == 0.5


def test_summarize_reports_none_for_retrieval_hit_rate_when_no_answerable_questions_present():
    outcomes = [
        QuestionOutcome(
            question_id="a", tenant_id="t1", category="baseline", retrieval_hit=None, grounded=True, internal_groundedness=None,
            honest_refusal=True, answer="", rewrite_count=0, low_confidence=False,
        ),
    ]

    summary = summarize("correction_on", outcomes)

    assert summary.retrieval_hit_rate is None
    assert summary.not_found_honesty == 1.0


def test_summarize_reports_none_for_not_found_honesty_when_no_unanswerable_questions_present():
    outcomes = [
        QuestionOutcome(
            question_id="a", tenant_id="t1", category="baseline", retrieval_hit=True, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
    ]

    summary = summarize("correction_on", outcomes)

    assert summary.retrieval_hit_rate == 1.0
    assert summary.not_found_honesty is None


# ---- summarize_by_category ----


def test_summarize_by_category_groups_outcomes_by_category():
    outcomes = [
        QuestionOutcome(
            question_id="a", tenant_id="t1", category="rewrite_bait", retrieval_hit=True, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=1, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="b", tenant_id="t1", category="rewrite_bait", retrieval_hit=False, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=1, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="c", tenant_id="t1", category="distractor_trap", retrieval_hit=True, grounded=False, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
    ]

    breakdown = summarize_by_category("correction_on", outcomes)

    assert set(breakdown.keys()) == {"rewrite_bait", "distractor_trap"}
    assert breakdown["rewrite_bait"].n_questions == 2
    assert breakdown["rewrite_bait"].retrieval_hit_rate == 0.5
    assert breakdown["distractor_trap"].n_questions == 1
    assert breakdown["distractor_trap"].groundedness_rate == 0.0


def test_summarize_by_category_orders_known_categories_before_unknown_ones():
    outcomes = [
        QuestionOutcome(
            question_id="a", tenant_id="t1", category="distractor_trap", retrieval_hit=True, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="b", tenant_id="t1", category="baseline", retrieval_hit=True, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
        QuestionOutcome(
            question_id="c", tenant_id="t1", category="rewrite_bait", retrieval_hit=True, grounded=True, internal_groundedness=None,
            honest_refusal=None, answer="", rewrite_count=0, low_confidence=False,
        ),
    ]

    breakdown = summarize_by_category("correction_on", outcomes)

    assert list(breakdown.keys()) == ["baseline", "rewrite_bait", "distractor_trap"]


# ---- build_question_transcript ----


def test_build_question_transcript_includes_chunks_answers_and_both_verdicts():
    question = _question()
    result_on = GraphState(
        question=question.question,
        tenant_id="t1",
        retrieved_chunks=[_chunk("a.md", "the answer is x")],
        answer="x is the answer",
        groundedness=True,
        groundedness_failure_reason=None,
    )
    result_off = GraphState(
        question=question.question,
        tenant_id="t1",
        retrieved_chunks=[_chunk("a.md", "the answer is x")],
        answer="x is the answer",
    )
    verdict_on = JudgeVerdict(grounded=True, unsupported_claims=[], reason="fully supported")
    verdict_off = JudgeVerdict(grounded=False, unsupported_claims=["x is the answer"], reason="not in sources")

    transcript = build_question_transcript(question, result_on, verdict_on, result_off, verdict_off)

    assert transcript["question_id"] == "q1"
    assert transcript["category"] == "baseline"
    assert transcript["correction_on"]["retrieved_chunks_passed_to_judge"][0]["text"] == "the answer is x"
    assert transcript["correction_on"]["judge_verdict"]["grounded"] is True
    assert transcript["correction_on"]["pipeline_internal_groundedness"] is True
    assert transcript["correction_off"]["judge_verdict"]["grounded"] is False
    assert transcript["correction_off"]["pipeline_internal_groundedness"] is None


def test_build_question_transcript_includes_grades_and_rewrite_trace():
    question = _question(category="multi_chunk")
    result_on = GraphState(
        question=question.question,
        tenant_id="t1",
        retrieved_chunks=[_chunk("a.md", "chunk a text"), _chunk("b.md", "chunk b text", chunk_id="c2")],
        grades=[
            ChunkGrade(chunk_id="c1", relevant=True, reason="on topic for the first half of the question"),
            ChunkGrade(chunk_id="c2", relevant=False, reason="does not mention the required entity"),
        ],
        rewrite_count=1,
        trace=[
            TraceEntry(node="retrieve", message="Retrieved 2 chunk(s)"),
            TraceEntry(node="grade", message="Graded 2 chunk(s): 1 relevant"),
            TraceEntry(node="rewrite", message="Rewrote question to: 'expanded question'"),
        ],
        answer="partial answer covering only chunk a",
    )
    result_off = GraphState(
        question=question.question,
        tenant_id="t1",
        retrieved_chunks=[_chunk("a.md", "chunk a text"), _chunk("b.md", "chunk b text", chunk_id="c2")],
        answer="full answer",
    )
    verdict_on = JudgeVerdict(grounded=False, unsupported_claims=["a claim about chunk b's fact"], reason="missing")
    verdict_off = JudgeVerdict(grounded=True, unsupported_claims=[], reason="fully supported")

    transcript = build_question_transcript(question, result_on, verdict_on, result_off, verdict_off)

    on_grades = transcript["correction_on"]["grades"]
    assert on_grades[0] == {"chunk_id": "c1", "relevant": True, "reason": "on topic for the first half of the question"}
    assert on_grades[1]["relevant"] is False
    assert transcript["correction_on"]["rewrite_count"] == 1
    assert [t["node"] for t in transcript["correction_on"]["trace"]] == ["retrieve", "grade", "rewrite"]
    assert transcript["correction_off"]["grades"] == []


# ---- render_results_md ----


def test_render_results_md_includes_all_three_metrics_and_a_delta_column():
    summary_on = RunSummary(
        config="correction_on", n_questions=25, retrieval_hit_rate=0.9, groundedness_rate=0.95, not_found_honesty=1.0
    )
    summary_off = RunSummary(
        config="correction_off", n_questions=25, retrieval_hit_rate=0.7, groundedness_rate=0.8, not_found_honesty=0.6
    )

    markdown = render_results_md(summary_on, summary_off)

    assert "Retrieval hit rate" in markdown
    assert "Groundedness rate" in markdown
    assert "Not-found honesty" in markdown
    assert "90.0%" in markdown
    assert "70.0%" in markdown


def test_render_results_md_shows_na_instead_of_zero_percent_for_inapplicable_metrics():
    summary_on = RunSummary(
        config="correction_on", n_questions=4, retrieval_hit_rate=None, groundedness_rate=1.0, not_found_honesty=1.0
    )
    summary_off = RunSummary(
        config="correction_off", n_questions=4, retrieval_hit_rate=None, groundedness_rate=1.0, not_found_honesty=1.0
    )

    markdown = render_results_md(summary_on, summary_off)

    assert "| Retrieval hit rate | n/a | n/a | n/a |" in markdown


# ---- render_category_breakdown_md ----


def test_render_category_breakdown_md_includes_a_section_per_category():
    summary_on = RunSummary(
        config="correction_on:rewrite_bait", n_questions=6, retrieval_hit_rate=1.0, groundedness_rate=1.0, not_found_honesty=0.0
    )
    summary_off = RunSummary(
        config="correction_off:rewrite_bait", n_questions=6, retrieval_hit_rate=0.5, groundedness_rate=0.8, not_found_honesty=0.0
    )

    markdown = render_category_breakdown_md({"rewrite_bait": summary_on}, {"rewrite_bait": summary_off})

    assert "rewrite_bait" in markdown
    assert "n=6" in markdown
    assert "100.0%" in markdown
    assert "50.0%" in markdown
