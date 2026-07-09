from app.eval.schemas import ExpectedChunk, GoldenQuestion, JudgeVerdict, QuestionOutcome, RunSummary


def test_golden_question_defaults_to_answerable_with_empty_chunk_list():
    question = GoldenQuestion(id="q1", tenant_id="demo-acme-legal", question="what is x?")

    assert question.unanswerable is False
    assert question.expected_answer_facts == []
    assert question.expected_chunks == []
    assert question.category == "baseline"


def test_golden_question_accepts_explicit_category():
    question = GoldenQuestion(id="q1", tenant_id="demo-acme-legal", question="what is x?", category="rewrite_bait")

    assert question.category == "rewrite_bait"


def test_golden_question_accepts_expected_chunks():
    question = GoldenQuestion(
        id="q1",
        tenant_id="demo-acme-legal",
        question="what is x?",
        expected_answer_facts=["x is 5"],
        expected_chunks=[ExpectedChunk(doc_name="a.md", contains="x is 5")],
    )

    assert question.expected_chunks[0].doc_name == "a.md"
    assert question.expected_chunks[0].contains == "x is 5"


def test_judge_verdict_requires_grounded_and_reason():
    verdict = JudgeVerdict(grounded=True, unsupported_claims=[], reason="fully supported")

    assert verdict.grounded is True
    assert verdict.unsupported_claims == []


def test_question_outcome_allows_none_for_inapplicable_fields():
    outcome = QuestionOutcome(
        question_id="q1",
        tenant_id="demo-acme-legal",
        category="near_miss_unanswerable",
        retrieval_hit=None,
        grounded=True,
        internal_groundedness=None,
        honest_refusal=True,
        answer="not found in the documents",
        rewrite_count=0,
        low_confidence=False,
    )

    assert outcome.retrieval_hit is None
    assert outcome.honest_refusal is True


def test_run_summary_holds_all_three_metrics():
    summary = RunSummary(
        config="correction_on",
        n_questions=25,
        retrieval_hit_rate=0.9,
        groundedness_rate=0.95,
        not_found_honesty=1.0,
    )

    assert summary.n_questions == 25
    assert summary.retrieval_hit_rate == 0.9
