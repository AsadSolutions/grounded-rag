from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    tenant_id: str
    doc_id: str
    doc_name: str
    chunk_index: int
    text: str
    content_hash: str | None = None


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
