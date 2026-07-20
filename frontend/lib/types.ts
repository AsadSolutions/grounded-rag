export type DemoTenant = {
  id: string;
  name: string;
  description: string;
  documentCount: number;
  suggestedQuestion: string;
  isDemo: boolean;
};

export type Tenant = {
  id: string;
  name: string;
  expiresAt?: string;
};

export type Document = {
  id: string;
  tenantId: string;
  name: string;
  chunkCount: number;
  uploadedAt: string | null;
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

export type TracedChunk = {
  chunkId: string;
  docName: string;
  chunkIndex: number;
};

export type TracedGrade = {
  chunkId: string;
  docName: string;
  chunkIndex: number;
  relevant: boolean;
  reason?: string;
};

export type TraceEntry =
  | { step: "retrieve"; query: string; chunks: TracedChunk[] }
  | { step: "grade"; grades: TracedGrade[] }
  | {
      step: "rewrite";
      attempt: number;
      originalQuery: string;
      rewrittenQuery: string;
    }
  | { step: "generate"; attempt: number; isRegeneration: boolean; answer: string }
  | {
      step: "groundedness_check";
      verdict: "grounded" | "not_grounded";
      reason?: string;
    }
  | { step: "log"; node: string; message: string };

export type ChatTrace = {
  steps: TraceEntry[];
  rewriteCount: number;
  regenerated: boolean;
  lowConfidence: boolean;
  skippedPipeline: boolean;
};

export type ChatEvent =
  | { type: "token"; value: string }
  | { type: "stage"; label: string }
  | { type: "sources"; chunks: RetrievedChunk[] }
  | { type: "trace"; trace: ChatTrace }
  | { type: "error"; message: string };

export type EvalMetric = {
  name: string;
  withCorrection: number;
  withoutCorrection: number;
  delta: number;
};

export type JudgeAgreement = {
  agreementRate: number;
  agreed: number;
  total: number;
};

export type EvalResults = {
  generatedAt: string;
  sample: boolean;
  metrics: EvalMetric[];
  judgeAgreement: JudgeAgreement;
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
