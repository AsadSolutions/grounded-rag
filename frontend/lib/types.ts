// Single source of truth for every type shared between lib/api.ts, lib/real-api.ts,
// lib/mocks/, and the components that consume them. Mirrors the GraphState fields
// and node list documented in docs/ARCHITECTURE.md.

export type DemoTenant = {
  id: string;
  name: string;
  description: string;
};

export type Tenant = {
  id: string;
  name: string;
  /** ISO 8601 timestamp. Present for scratch tenants, absent for demo tenants. */
  expiresAt?: string;
};

export type Document = {
  id: string;
  tenantId: string;
  name: string;
  chunkCount: number;
  /** ISO 8601 timestamp. */
  uploadedAt: string;
};

export type RetrievedChunk = {
  chunkId: string;
  docId: string;
  docName: string;
  chunkIndex: number;
  text: string;
  score: number;
};

export type ChunkGrade = {
  chunkId: string;
  relevant: boolean;
  reason?: string;
};

export type TraceEntry =
  | { step: "retrieve"; query: string; chunks: RetrievedChunk[] }
  | { step: "grade"; grades: ChunkGrade[] }
  | {
      step: "rewrite";
      attempt: number;
      originalQuery: string;
      rewrittenQuery: string;
    }
  | { step: "generate"; attempt: number }
  | {
      step: "groundedness_check";
      verdict: "grounded" | "not_grounded";
      reason?: string;
    };

export type ChatTrace = {
  steps: TraceEntry[];
  rewriteCount: number;
  regenerated: boolean;
  lowConfidence: boolean;
};

export type ChatEvent =
  | { type: "token"; value: string }
  | { type: "sources"; chunks: RetrievedChunk[] }
  | { type: "trace"; trace: ChatTrace }
  | { type: "error"; message: string };

export type EvalMetric = {
  name: string;
  withCorrection: number;
  withoutCorrection: number;
  delta: number;
};

export type EvalResults = {
  /** ISO 8601 timestamp of the eval run. */
  generatedAt: string;
  /** True when these numbers are illustrative sample data, not a real eval run. */
  sample: boolean;
  metrics: EvalMetric[];
};

export type ApiClient = {
  getDemoTenants: () => Promise<DemoTenant[]>;
  createTenant: () => Promise<Tenant>;
  listDocuments: (tenantId: string) => Promise<Document[]>;
  uploadDocument: (
    tenantId: string,
    file: File,
    onProgress?: (pct: number) => void,
  ) => Promise<Document>;
  deleteDocument: (tenantId: string, documentId: string) => Promise<void>;
  chat: (
    tenantId: string,
    question: string,
    signal?: AbortSignal,
  ) => AsyncGenerator<ChatEvent>;
  getEvalResults: () => Promise<EvalResults>;
};
