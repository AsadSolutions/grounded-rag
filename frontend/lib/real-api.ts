import type {
  ApiClient,
  ChatEvent,
  ChunkGrade,
  DemoTenant,
  Document,
  EvalResults,
  RetrievedChunk,
  Tenant,
  TraceEntry,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
  uploaded_at: string;
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
function toGrade(raw: ChunkGradeResponse): ChunkGrade {
  return { chunkId: raw.chunk_id, relevant: raw.relevant, reason: raw.reason };
}

type TraceEntryResponse =
  | { step: "retrieve"; query: string; chunks: ChunkResponse[] }
  | { step: "grade"; grades: ChunkGradeResponse[] }
  | {
      step: "rewrite";
      attempt: number;
      original_query: string;
      rewritten_query: string;
    }
  | { step: "generate"; attempt: number }
  | {
      step: "groundedness_check";
      verdict: "grounded" | "not_grounded";
      reason?: string;
    };

function toTraceEntry(raw: TraceEntryResponse): TraceEntry {
  switch (raw.step) {
    case "retrieve":
      return {
        step: "retrieve",
        query: raw.query,
        chunks: raw.chunks.map(toChunk),
      };
    case "grade":
      return { step: "grade", grades: raw.grades.map(toGrade) };
    case "rewrite":
      return {
        step: "rewrite",
        attempt: raw.attempt,
        originalQuery: raw.original_query,
        rewrittenQuery: raw.rewritten_query,
      };
    case "generate":
      return { step: "generate", attempt: raw.attempt };
    case "groundedness_check":
      return {
        step: "groundedness_check",
        verdict: raw.verdict,
        reason: raw.reason,
      };
  }
}

type EvalMetricResponse = {
  name: string;
  with_correction: number;
  without_correction: number;
  delta: number;
};
type EvalResultsResponse = {
  generated_at: string;
  sample: boolean;
  metrics: EvalMetricResponse[];
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
      resolve(toDocument(JSON.parse(xhr.responseText) as DocumentResponse));
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

function parseSseFrame(rawFrame: string): ChatEvent {
  let eventName = "message";
  const dataLines: string[] = [];
  for (const line of rawFrame.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  const raw = dataLines.join("\n");
  const payload = raw ? JSON.parse(raw) : {};

  switch (eventName) {
    case "token":
      return { type: "token", value: payload.value };
    case "sources":
      return {
        type: "sources",
        chunks: (payload.chunks as ChunkResponse[]).map(toChunk),
      };
    case "trace":
      return {
        type: "trace",
        trace: {
          steps: (payload.steps as TraceEntryResponse[]).map(toTraceEntry),
          rewriteCount: payload.rewrite_count,
          regenerated: payload.regenerated,
          lowConfidence: payload.low_confidence,
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
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const rawFrame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        if (rawFrame.trim().length > 0) {
          yield parseSseFrame(rawFrame);
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
