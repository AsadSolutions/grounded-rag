from pydantic import BaseModel, Field


class ExpectedChunk(BaseModel):
    doc_name: str
    contains: str


class GoldenQuestion(BaseModel):
    id: str
    tenant_id: str
    question: str
    category: str = "baseline"
    expected_answer_facts: list[str] = Field(default_factory=list)
    expected_chunks: list[ExpectedChunk] = Field(default_factory=list)
    unanswerable: bool = False


class JudgeVerdict(BaseModel):
    grounded: bool
    unsupported_claims: list[str]
    reason: str


class QuestionOutcome(BaseModel):
    question_id: str
    tenant_id: str
    category: str
    retrieval_hit: bool | None
    grounded: bool
    internal_groundedness: bool | None
    honest_refusal: bool | None
    answer: str
    rewrite_count: int
    low_confidence: bool


class RunSummary(BaseModel):
    config: str
    n_questions: int
    retrieval_hit_rate: float | None
    groundedness_rate: float
    not_found_honesty: float | None
