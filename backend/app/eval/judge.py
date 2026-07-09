"""Independent groundedness judge for the eval harness.

Deliberately a different prompt and framing from app.graph.nodes's internal
check_groundedness_llm: this judge is told explicitly that it is auditing,
not generating, is instructed to extract and check claims one at a time
rather than eyeball the whole answer, and lists every unsupported claim
verbatim instead of returning a single reason string. The eval harness must
not grade itself with the same self-assessment logic the pipeline uses
internally.

The model is never asked to produce the `grounded` boolean directly. An
earlier version had the LLM emit grounded, unsupported_claims, and reason as
three independent structured-output fields in that order — but OpenAI's
structured output decodes JSON fields in schema-declaration order, so the
model committed to grounded before it had done the claim-by-claim extraction
that was supposed to justify it. In practice this produced self-contradictory
verdicts (grounded=false with unsupported_claims=[] and a reason stating the
answer was fully supported). grounded is now derived deterministically in
code from whether unsupported_claims is empty, so that contradiction is
structurally impossible rather than merely unlikely.
"""

from pydantic import BaseModel

from app.config import get_settings
from app.eval.schemas import JudgeVerdict
from app.models import ScoredChunk


def _openai_client():
    from openai import OpenAI

    return OpenAI(api_key=get_settings().openai_api_key)


_JUDGE_SYSTEM_PROMPT = (
    "You are an independent fact-checking auditor. You did not write the answer below and "
    "have no stake in it being correct. Extract every discrete factual claim the answer "
    "makes, then check each claim against the sources one at a time, judging the meaning of "
    "the claim against the meaning of the sources, not the exact wording.\n\n"
    "A claim is SUPPORTED, and must not be listed in unsupported_claims, if it is a faithful "
    "paraphrase, rewording, summary, or unit conversion of something the sources state, or if "
    "it resolves a pronoun or reference (like 'they' or 'it') to an entity the sources name in "
    "the same context. Combining several sentences from the sources into one, or restating a "
    "number or rule in different words, is not a fabrication.\n\n"
    "A claim is UNSUPPORTED only if it introduces a specific fact, number, entity, exception, "
    "or condition that the sources do not state and cannot be reasonably derived from what they "
    "do state. When in doubt between 'the sources imply this' and 'this is invented', treat it "
    "as supported — your job is to catch hallucination and invented specifics, not to penalize "
    "normal paraphrasing.\n\n"
    "List every unsupported claim verbatim in unsupported_claims — leave it empty if every claim "
    "is supported. An answer that says the information was not found in the documents, and makes "
    "no other factual claims, has no unsupported claims. You do not decide grounded or not "
    "grounded yourself; that is derived automatically from unsupported_claims, so focus entirely "
    "on making that list accurate."
)


class _JudgeExtraction(BaseModel):
    unsupported_claims: list[str]
    reason: str


def judge_groundedness(question: str, answer: str, chunks: list[ScoredChunk]) -> JudgeVerdict:
    settings = get_settings()
    sources = "\n\n".join(f"[{chunk.chunk_id}] {chunk.text}" for chunk in chunks)
    response = _openai_client().chat.completions.parse(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer}\n\nSources:\n{sources}"},
        ],
        response_format=_JudgeExtraction,
    )
    extraction = response.choices[0].message.parsed
    return JudgeVerdict(
        grounded=len(extraction.unsupported_claims) == 0,
        unsupported_claims=extraction.unsupported_claims,
        reason=extraction.reason,
    )
