"""Pre-graph intent short-circuit: smalltalk and document-meta questions
never touch the retrieval graph. Kept separate from app/graph/ (CLAUDE.md
rule 6 — graph wiring stays in app/graph/, never mixed with anything
else) and does not modify any of the locked pipeline prompts.
"""

import logging
import re
from typing import Literal

from pydantic import BaseModel

from app.config import get_settings
from app.document_catalog import list_tenant_documents

logger = logging.getLogger(__name__)

IntentLabel = Literal["smalltalk", "document_meta", "document_question"]


_GREETING_PATTERN = re.compile(
    r"^(hi|hello|hey|hiya|yo)([,!]?\s*(there|team))?[!.]*$"
    r"|^good (morning|afternoon|evening)[!.]*$"
    r"|^((hi|hello|hey)[,!]?\s*)?how are you\??$",
    re.IGNORECASE,
)
_GRATITUDE_PATTERN = re.compile(
    r"^(thanks|thank you|thx|cheers)(\s+(a lot|so much))?[!.]*$", re.IGNORECASE
)
_CAPABILITY_PATTERN = re.compile(
    r"^(what can you do|who are you|what are you)\??$", re.IGNORECASE
)
_DOCUMENT_META_PATTERN = re.compile(
    r"(how many documents?(\s+(do you have|are there|have you got))?"
    r"|what documents? do you have"
    r"|which documents? do you have"
    r"|list (your|the|all) documents?"
    r"|documents? do you have)\??$",
    re.IGNORECASE,
)


def _openai_client():
    from openai import OpenAI

    return OpenAI(api_key=get_settings().openai_api_key)



_FallbackIntentLabel = Literal["document_meta", "document_question"]


class _IntentClassification(BaseModel):
    intent: _FallbackIntentLabel


def classify_intent_llm(question: str) -> IntentLabel:
    settings = get_settings()
    try:
        response = _openai_client().chat.completions.parse(
            model=settings.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify the user's message as exactly one of: "
                        "'document_meta' (asking how many or which "
                        "documents/files are available) or 'document_question' "
                        "(anything else, including unclear, garbled, or "
                        "ambiguous text). Greetings, thanks, and capability "
                        "questions are already handled before you see this "
                        "message, so never classify anything as casual "
                        "conversation — if in doubt, choose 'document_question' "
                        "so the retrieval pipeline gets a chance to answer or "
                        "say the information wasn't found."
                    ),
                },
                {"role": "user", "content": question},
            ],
            response_format=_IntentClassification,
        )
        return response.choices[0].message.parsed.intent
    except Exception:
        logger.exception(
            "Intent classification failed for question=%r; treating as a document question", question
        )
        return "document_question"


def classify_intent(question: str, *, classify_fn=classify_intent_llm) -> IntentLabel:
    normalized = question.strip()
    if _DOCUMENT_META_PATTERN.search(normalized):
        return "document_meta"
    if (
        _GREETING_PATTERN.match(normalized)
        or _GRATITUDE_PATTERN.match(normalized)
        or _CAPABILITY_PATTERN.match(normalized)
    ):
        return "smalltalk"
    return classify_fn(normalized)


def answer_smalltalk(question: str) -> str:
    normalized = question.strip()
    if _GRATITUDE_PATTERN.match(normalized):
        return "You're welcome! Let me know if you have more questions about your documents."
    if _CAPABILITY_PATTERN.match(normalized):
        return (
            "I answer questions using the documents uploaded to this workspace. "
            "Ask me anything about their content, or upload more to get started."
        )
    return "Hi! How can I help you with your documents today?"


def answer_document_meta(tenant_id: str, *, list_fn=list_tenant_documents) -> str:
    documents = list_fn(tenant_id)
    if not documents:
        return "You don't have any documents uploaded yet. Upload a PDF, TXT, or MD file to get started."
    plural = "document" if len(documents) == 1 else "documents"
    names = "\n".join(f"- {doc.name}" for doc in documents)
    return f"You have {len(documents)} {plural}:\n{names}"
