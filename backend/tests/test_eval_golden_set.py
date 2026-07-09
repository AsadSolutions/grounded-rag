from app.eval.run import load_golden_set

EXPECTED_CATEGORY_COUNTS = {
    "baseline": 25,
    "rewrite_bait": 6,
    "multi_chunk": 5,
    "distractor_trap": 5,
    "near_miss_unanswerable": 4,
}


def test_golden_set_has_45_questions():
    questions = load_golden_set()

    assert len(questions) == 45


def test_golden_set_has_exactly_nine_unanswerable_questions():
    questions = load_golden_set()

    unanswerable = [q for q in questions if q.unanswerable]
    assert len(unanswerable) == 9


def test_golden_set_answerable_questions_have_expected_chunks_and_facts():
    questions = load_golden_set()

    for question in questions:
        if not question.unanswerable:
            assert question.expected_chunks, f"{question.id} is answerable but has no expected_chunks"
            assert question.expected_answer_facts, f"{question.id} is answerable but has no expected_answer_facts"


def test_golden_set_unanswerable_questions_have_no_expected_chunks_or_facts():
    questions = load_golden_set()

    for question in questions:
        if question.unanswerable:
            assert question.expected_chunks == []
            assert question.expected_answer_facts == []


def test_golden_set_ids_are_unique():
    questions = load_golden_set()

    ids = [q.id for q in questions]
    assert len(ids) == len(set(ids))


def test_golden_set_only_references_the_two_demo_tenants():
    questions = load_golden_set()

    tenant_ids = {q.tenant_id for q in questions}
    assert tenant_ids <= {"demo-acme-legal", "demo-techcorp"}


def test_golden_set_category_counts_match_the_hardening_spec():
    questions = load_golden_set()

    counts: dict[str, int] = {}
    for question in questions:
        counts[question.category] = counts.get(question.category, 0) + 1

    assert counts == EXPECTED_CATEGORY_COUNTS


def test_golden_set_near_miss_unanswerable_questions_are_marked_unanswerable():
    questions = load_golden_set()

    near_miss = [q for q in questions if q.category == "near_miss_unanswerable"]
    assert len(near_miss) == 4
    assert all(q.unanswerable for q in near_miss)


def test_golden_set_multi_chunk_questions_reference_at_least_two_expected_chunks():
    questions = load_golden_set()

    multi_chunk = [q for q in questions if q.category == "multi_chunk"]
    assert len(multi_chunk) == 5
    for question in multi_chunk:
        assert len(question.expected_chunks) >= 2, f"{question.id} is multi_chunk but has fewer than 2 expected_chunks"
