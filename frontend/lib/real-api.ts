import type {
  ApiClient,
  ChatEvent,
  DemoTenant,
  Document,
  EvalResults,
  RetrievedChunk,
  Tenant,
  TraceEntry,
} from "@/lib/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(
      `GroundedRAG API ${init?.method ?? "GET"} ${path} failed: ${response.status} ${response.statusText}${body ? ` — ${body}` : ""}`,
    );
  }
  return response;
}

async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init);
  return response.json() as Promise<T>;
}

type DemoTenantResponse = {
  id: string;
  name: string;
  description: string;
  document_count: number;
  suggested_question: string;
};
function toDemoTenant(raw: DemoTenantResponse): DemoTenant {
  return {
    id: raw.id,
    name: raw.name,
    description: raw.description,
    documentCount: raw.document_count,
    suggestedQuestion: raw.suggested_question,
    isDemo: true,
  };
}

type TenantResponse = { tenant_id: string; name: string; expires_at?: string };
function toTenant(raw: TenantResponse): Tenant {
  return { id: raw.tenant_id, name: raw.name, expiresAt: raw.expires_at };
}

type DocumentResponse = {
  id: string;
  tenant_id: string;
  name: string;
  chunk_count: number;
  uploaded_at: string | null;
};
function toDocument(raw: DocumentResponse): Document {
  return {
    id: raw.id,
    tenantId: raw.tenant_id,
    name: raw.name,
    chunkCount: raw.chunk_count,
    uploadedAt: raw.uploaded_at,
  };
}

type IngestResultResponse = {
  doc_id: string;
  doc_name: string;
  tenant_id: string;
  chunk_count: number;
};
function toDocumentFromIngestResult(raw: IngestResultResponse): Document {
  return {
    id: raw.doc_id,
    tenantId: raw.tenant_id,
    name: raw.doc_name,
    chunkCount: raw.chunk_count,
    uploadedAt: new Date().toISOString(),
  };
}

type ChunkResponse = {
  chunk_id: string;
  doc_id: string;
  doc_name: string;
  chunk_index: number;
  text: string;
  score: number;
};
function toChunk(raw: ChunkResponse): RetrievedChunk {
  return {
    chunkId: raw.chunk_id,
    docId: raw.doc_id,
    docName: raw.doc_name,
    chunkIndex: raw.chunk_index,
    text: raw.text,
    score: raw.score,
  };
}

type ChunkGradeResponse = {
  chunk_id: string;
  relevant: boolean;
  reason?: string;
};
type TracedChunkResponse = {
  chunk_id: string;
  doc_name: string;
  chunk_index: number;
};
type TracedGradeResponse = {
  chunk_id: string;
  doc_name: string;
  chunk_index: number;
  relevant: boolean;
  reason?: string;
};
type TraceEntryResponse = {
  node: string;
  message: string;
  query?: string;
  chunk_ids?: string[];
  chunks?: TracedChunkResponse[];
  grades?: ChunkGradeResponse[];
  graded_chunks?: TracedGradeResponse[];
  old_query?: string;
  new_query?: string;
  is_regeneration?: boolean;
  answer?: string;
  grounded?: boolean;
  unsupported_claims?: string[];
};

function makeTraceEntryMapper(): (raw: TraceEntryResponse) => TraceEntry {
  let rewriteAttempts = 0;
  let generateAttempts = 0;

  return (raw: TraceEntryResponse): TraceEntry => {
    switch (raw.node) {
      case "retrieve":
        if (raw.query !== undefined && raw.chunks) {
          return {
            step: "retrieve",
            query: raw.query,
            chunks: raw.chunks.map((c) => ({
              chunkId: c.chunk_id,
              docName: c.doc_name,
              chunkIndex: c.chunk_index,
            })),
          };
        }
        break;
      case "grade":
        if (raw.graded_chunks) {
          return {
            step: "grade",
            grades: raw.graded_chunks.map((g) => ({
              chunkId: g.chunk_id,
              docName: g.doc_name,
              chunkIndex: g.chunk_index,
              relevant: g.relevant,
              reason: g.reason,
            })),
          };
        }
        break;
      case "rewrite":
        if (raw.old_query !== undefined && raw.new_query !== undefined) {
          rewriteAttempts += 1;
          return {
            step: "rewrite",
            attempt: rewriteAttempts,
            originalQuery: raw.old_query,
            rewrittenQuery: raw.new_query,
          };
        }
        break;
      case "generate":
        if (raw.is_regeneration !== undefined && raw.answer !== undefined) {
          generateAttempts += 1;
          return {
            step: "generate",
            attempt: generateAttempts,
            isRegeneration: raw.is_regeneration,
            answer: raw.answer,
          };
        }
        break;
      case "groundedness_check":
        if (raw.grounded !== undefined) {
          const claims = raw.unsupported_claims ?? [];
          return {
            step: "groundedness_check",
            verdict: raw.grounded ? "grounded" : "not_grounded",
            reason: claims.length > 0 ? claims.join("; ") : undefined,
          };
        }
        break;
    }
    return { step: "log", node: raw.node, message: raw.message };
  };
}

type EvalMetricResponse = {
  name: string;
  with_correction: number;
  without_correction: number;
  delta: number;
};
type JudgeAgreementResponse = {
  agreement_rate: number;
  agreed: number;
  total: number;
};
type EvalResultsResponse = {
  generated_at: string;
  sample: boolean;
  metrics: EvalMetricResponse[];
  judge_agreement: JudgeAgreementResponse;
};
function toEvalResults(raw: EvalResultsResponse): EvalResults {
  return {
    generatedAt: raw.generated_at,
    sample: raw.sample,
    metrics: raw.metrics.map((m) => ({
      name: m.name,
      withCorrection: m.with_correction,
      withoutCorrection: m.without_correction,
      delta: m.delta,
    })),
    judgeAgreement: {
      agreementRate: raw.judge_agreement.agreement_rate,
      agreed: raw.judge_agreement.agreed,
      total: raw.judge_agreement.total,
    },
  };
}

async function getDemoTenants(): Promise<DemoTenant[]> {
  const raw = await apiJson<DemoTenantResponse[]>("/api/tenants/demo");
  return raw.map(toDemoTenant);
}

async function createTenant(): Promise<Tenant> {
  const raw = await apiJson<TenantResponse>("/api/tenants", { method: "POST" });
  return toTenant(raw);
}

async function listDocuments(tenantId: string): Promise<Document[]> {
  const raw = await apiJson<DocumentResponse[]>(
    `/api/documents?tenant_id=${encodeURIComponent(tenantId)}`,
  );
  return raw.map(toDocument);
}

async function uploadDocument(
  tenantId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<Document> {
  const formData = new FormData();
  formData.append("tenant_id", tenantId);
  formData.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/api/documents`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress?.(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onerror = () => {
      reject(
        new Error("GroundedRAG API POST /api/documents failed: network error"),
      );
    };

    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(
          new Error(
            `GroundedRAG API POST /api/documents failed: ${xhr.status} ${xhr.statusText} — ${xhr.responseText}`,
          ),
        );
        return;
      }
      resolve(
        toDocumentFromIngestResult(
          JSON.parse(xhr.responseText) as IngestResultResponse,
        ),
      );
    };

    xhr.send(formData);
  });
}

async function deleteDocument(
  tenantId: string,
  documentId: string,
): Promise<void> {
  await apiFetch(
    `/api/documents/${encodeURIComponent(documentId)}?tenant_id=${encodeURIComponent(tenantId)}`,
    { method: "DELETE" },
  );
}

function parseSseFrame(rawFrame: string): ChatEvent | null {
  let eventName: string | null = null;
  const dataLines: string[] = [];
  for (const line of rawFrame.split("\n")) {
    if (line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (eventName === null) {
    return null;
  }

  const raw = dataLines.join("\n");
  const payload = raw ? JSON.parse(raw) : {};

  switch (eventName) {
    case "token":
      return { type: "token", value: payload.token };

    case "stage":
      return { type: "stage", label: payload.label };
    case "sources":
      return {
        type: "sources",
        chunks: (payload as ChunkResponse[]).map(toChunk),
      };

    case "trace":
      return {
        type: "trace",
        trace: {
          steps: (payload.entries as TraceEntryResponse[]).map(
            makeTraceEntryMapper(),
          ),
          rewriteCount: payload.rewrite_count,
          regenerated: payload.regenerated,
          lowConfidence: payload.low_confidence,
          skippedPipeline: payload.skipped_pipeline,
        },
      };
    case "error":
      return { type: "error", message: payload.message };
    default:
      throw new Error(`GroundedRAG API: unrecognized SSE event "${eventName}"`);
  }
}

async function* chat(
  tenantId: string,
  question: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_id: tenantId, question }),
    signal,
  });

  if (!response.ok || !response.body) {
    const body = await response.text().catch(() => "");
    throw new Error(
      `GroundedRAG API POST /api/chat failed: ${response.status} ${response.statusText}${body ? ` — ${body}` : ""}`,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const rawFrame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        if (rawFrame.trim().length > 0) {
          const event = parseSseFrame(rawFrame);
          if (event) yield event;
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return;
    }
    yield {
      type: "error",
      message: err instanceof Error ? err.message : "Unknown streaming error.",
    };
  }
}

async function getEvalResults(): Promise<EvalResults> {
  const raw = await apiJson<EvalResultsResponse>("/api/eval/results");
  return toEvalResults(raw);
}

export const realClient: ApiClient = {
  getDemoTenants,
  createTenant,
  listDocuments,
  uploadDocument,
  deleteDocument,
  chat,
  getEvalResults,
};
