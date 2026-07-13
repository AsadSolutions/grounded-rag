"""Unit tests for the pre-graph intent classifier and its canned replies.
Fast-path regex cases never touch OpenAI; the LLM fallback is exercised
with an injected fake so no real API call happens.
"""

import pytest
from pydantic import ValidationError

from app.chat_intent import _IntentClassification, answer_document_meta, answer_smalltalk, classify_intent
from app.models import DocumentSummary


def test_classify_intent_matches_bare_greetings():
    assert classify_intent("hi") == "smalltalk"
    assert classify_intent("Hello!") == "smalltalk"
    assert classify_intent("hey there") == "smalltalk"
    assert classify_intent("good morning") == "smalltalk"


def test_classify_intent_matches_gratitude():
    assert classify_intent("thanks") == "smalltalk"
    assert classify_intent("Thank you so much!") == "smalltalk"


def test_classify_intent_matches_capability_questions():
    assert classify_intent("what can you do?") == "smalltalk"
    assert classify_intent("Who are you") == "smalltalk"


def test_classify_intent_matches_document_count_questions():
    assert classify_intent("how many documents do you have?") == "document_meta"
    assert classify_intent("What documents do you have") == "document_meta"
    assert classify_intent("list your documents") == "document_meta"


def test_classify_intent_does_not_misfire_on_a_real_question_containing_a_greeting():
    calls = []
    classify_intent("hi, what does the contract say about refunds", classify_fn=calls.append)
    assert calls == ["hi, what does the contract say about refunds"]


def test_classify_intent_does_not_misfire_on_a_content_question_mentioning_documents():
    calls = []
    classify_intent("how many documents mention the termination clause", classify_fn=calls.append)
    assert calls == ["how many documents mention the termination clause"]


def test_classify_intent_falls_back_to_llm_for_ambiguous_phrasing():
    calls = []

    def fake_llm(question):
        calls.append(question)
        return "document_question"

    result = classify_intent("yo what's good", classify_fn=fake_llm)

    assert result == "document_question"
    assert calls == ["yo what's good"]


def test_classify_intent_sends_garbled_ambiguous_text_to_the_llm_fallback_not_smalltalk():
    # Regression: "Gohaul explain me" doesn't match any fast-path pattern,
    # so it must reach the LLM fallback rather than being silently treated
    # as smalltalk by a regex false positive.
    calls = []

    def fake_llm(question):
        calls.append(question)
        return "document_question"

    result = classify_intent("Gohaul explain me", classify_fn=fake_llm)

    assert result == "document_question"
    assert calls == ["Gohaul explain me"]


def test_llm_fallback_schema_cannot_produce_smalltalk():
    # The fallback must never be able to guess "smalltalk" itself — only the
    # deterministic fast-path regexes may. Otherwise ambiguous or garbled
    # text silently gets a canned greeting instead of a real answer attempt.
    with pytest.raises(ValidationError):
        _IntentClassification(intent="smalltalk")


def test_answer_smalltalk_distinguishes_gratitude_capability_and_greeting():
    assert "welcome" in answer_smalltalk("thanks").lower()
    assert "documents uploaded" in answer_smalltalk("what can you do").lower()
    assert "help" in answer_smalltalk("hello").lower()


def test_answer_document_meta_lists_documents_by_name():
    def fake_list(tenant_id):
        return [
            DocumentSummary(id="d1", tenant_id=tenant_id, name="handbook.pdf", chunk_count=10),
            DocumentSummary(id="d2", tenant_id=tenant_id, name="policy.md", chunk_count=4),
        ]

    reply = answer_document_meta("t1", list_fn=fake_list)

    assert "2 documents" in reply
    assert "handbook.pdf" in reply
    assert "policy.md" in reply


def test_answer_document_meta_handles_zero_documents():
    reply = answer_document_meta("t1", list_fn=lambda tenant_id: [])

    assert "don't have any documents" in reply.lower()
