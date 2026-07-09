import type {
  ApiClient,
  DemoTenant,
  Document,
  EvalResults,
  Tenant,
} from "@/lib/types";
import { DEMO_DOCUMENTS, DEMO_TENANTS } from "./fixtures";
import { mockChat } from "./chat";
import { mockUploadDocument } from "./upload";
import { MOCK_EVAL_RESULTS } from "./eval";

const SCRATCH_TENANT_TTL_MS = 24 * 60 * 60 * 1000;

const documentsByTenant: Record<string, Document[]> = Object.fromEntries(
  Object.entries(DEMO_DOCUMENTS).map(([tenantId, docs]) => [
    tenantId,
    [...docs],
  ]),
);

let scratchTenantCount = 0;

async function getDemoTenants(): Promise<DemoTenant[]> {
  return DEMO_TENANTS;
}

async function createTenant(): Promise<Tenant> {
  scratchTenantCount += 1;
  const id = `scratch-${scratchTenantCount}`;
  documentsByTenant[id] = [];
  return {
    id,
    name: `Scratch tenant ${scratchTenantCount}`,
    expiresAt: new Date(Date.now() + SCRATCH_TENANT_TTL_MS).toISOString(),
  };
}

async function listDocuments(tenantId: string): Promise<Document[]> {
  return documentsByTenant[tenantId] ?? [];
}

async function uploadDocument(
  tenantId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<Document> {
  const document = await mockUploadDocument(tenantId, file, onProgress);
  const existing = documentsByTenant[tenantId] ?? [];
  documentsByTenant[tenantId] = [...existing, document];
  return document;
}

async function deleteDocument(
  tenantId: string,
  documentId: string,
): Promise<void> {
  const existing = documentsByTenant[tenantId] ?? [];
  documentsByTenant[tenantId] = existing.filter((doc) => doc.id !== documentId);
}

async function getEvalResults(): Promise<EvalResults> {
  return MOCK_EVAL_RESULTS;
}

export const mockClient: ApiClient = {
  getDemoTenants,
  createTenant,
  listDocuments,
  uploadDocument,
  deleteDocument,
  chat: mockChat,
  getEvalResults,
};
