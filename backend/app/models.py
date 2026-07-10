from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    tenant_id: str
    doc_id: str
    doc_name: str
    chunk_index: int
    text: str
    content_hash: str | None = None
    uploaded_at: str | None = None


class ScoredChunk(Chunk):
    score: float


class IngestResult(BaseModel):
    doc_id: str
    doc_name: str
    tenant_id: str
    chunk_count: int


class ChunkGrade(BaseModel):
    chunk_id: str
    relevant: bool
    reason: str


class TraceEntry(BaseModel):
    node: str
    message: str
    query: str | None = None
    chunk_ids: list[str] | None = None
    grades: list[ChunkGrade] | None = None
    old_query: str | None = None
    new_query: str | None = None
    is_regeneration: bool | None = None
    grounded: bool | None = None
    unsupported_claims: list[str] | None = None


class GraphState(BaseModel):
    question: str
    tenant_id: str
    retrieved_chunks: list[ScoredChunk] = Field(default_factory=list)
    grades: list[ChunkGrade] = Field(default_factory=list)
    rewrite_count: int = 0
    answer: str = ""
    groundedness: bool | None = None
    groundedness_failure_reason: str | None = None
    regenerated: bool = False
    low_confidence: bool = False
    trace: list[TraceEntry] = Field(default_factory=list)


class ChatRequest(BaseModel):
    tenant_id: str
    question: str


class DocumentSummary(BaseModel):
    id: str
    tenant_id: str
    name: str
    chunk_count: int
    uploaded_at: str | None = None


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    expires_at: str


class DemoTenantResponse(BaseModel):
    id: str
    name: str
    description: str
    document_count: int
    suggested_question: str


class EvalMetric(BaseModel):
    name: str
    with_correction: float
    without_correction: float
    delta: float


class EvalResultsResponse(BaseModel):
    generated_at: str
    sample: bool
    metrics: list[EvalMetric]
