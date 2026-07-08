import { mockClient } from "@/lib/mocks";
import { realClient } from "@/lib/real-api";

// The only file in the codebase allowed to know whether mocks are on. Every
// call site imports the functions below and stays oblivious to the flag.
const client = process.env.NEXT_PUBLIC_USE_MOCKS === "true" ? mockClient : realClient;

export const {
  getDemoTenants,
  createTenant,
  listDocuments,
  uploadDocument,
  deleteDocument,
  chat,
  getEvalResults,
} = client;
