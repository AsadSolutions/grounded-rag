import type { Document, DemoTenant, RetrievedChunk } from "@/lib/types";

export const DEMO_TENANTS: DemoTenant[] = [
  {
    id: "acme-legal",
    name: "Acme Legal",
    description: "Contract templates, data processing policy, employee handbook.",
  },
  {
    id: "techcorp-handbook",
    name: "TechCorp Handbook",
    description: "Onboarding guide, API style guide, incident response runbook.",
  },
];

export const DEMO_DOCUMENTS: Record<string, Document[]> = {
  "acme-legal": [
    {
      id: "doc-employee-handbook",
      tenantId: "acme-legal",
      name: "Employee Handbook.pdf",
      chunkCount: 42,
      uploadedAt: "2026-06-01T09:00:00.000Z",
    },
    {
      id: "doc-data-processing-policy",
      tenantId: "acme-legal",
      name: "Data Processing Policy.pdf",
      chunkCount: 18,
      uploadedAt: "2026-06-01T09:02:00.000Z",
    },
    {
      id: "doc-vendor-contract-template",
      tenantId: "acme-legal",
      name: "Vendor Contract Template.md",
      chunkCount: 11,
      uploadedAt: "2026-06-01T09:03:00.000Z",
    },
  ],
  "techcorp-handbook": [
    {
      id: "doc-onboarding-guide",
      tenantId: "techcorp-handbook",
      name: "Onboarding Guide.md",
      chunkCount: 24,
      uploadedAt: "2026-06-02T09:00:00.000Z",
    },
    {
      id: "doc-api-style-guide",
      tenantId: "techcorp-handbook",
      name: "API Style Guide.md",
      chunkCount: 31,
      uploadedAt: "2026-06-02T09:01:00.000Z",
    },
    {
      id: "doc-incident-response-runbook",
      tenantId: "techcorp-handbook",
      name: "Incident Response Runbook.pdf",
      chunkCount: 27,
      uploadedAt: "2026-06-02T09:02:00.000Z",
    },
  ],
};

/**
 * A pool of realistic chunks per tenant, keyed by chunk id, used to build
 * plausible RetrievedChunk results in the chat mock.
 */
export const DEMO_CHUNKS: Record<string, RetrievedChunk[]> = {
  "acme-legal": [
    {
      chunkId: "chunk-handbook-014",
      docId: "doc-employee-handbook",
      docName: "Employee Handbook.pdf",
      chunkIndex: 14,
      text: "Employees accrue 1.25 days of paid time off per month, up to a maximum carryover of 10 unused days into the following calendar year. Unused days beyond the cap are forfeited on January 1st.",
      score: 0.91,
    },
    {
      chunkId: "chunk-handbook-022",
      docId: "doc-employee-handbook",
      docName: "Employee Handbook.pdf",
      chunkIndex: 22,
      text: "Remote employees are expected to be reachable during their designated core hours, which each team lead sets and documents in the team's onboarding doc.",
      score: 0.78,
    },
    {
      chunkId: "chunk-dpp-005",
      docId: "doc-data-processing-policy",
      docName: "Data Processing Policy.pdf",
      chunkIndex: 5,
      text: "Personal data collected from clients must be deleted within 30 days of contract termination unless a longer retention period is required by applicable law.",
      score: 0.86,
    },
    {
      chunkId: "chunk-vendor-002",
      docId: "doc-vendor-contract-template",
      docName: "Vendor Contract Template.md",
      chunkIndex: 2,
      text: "Either party may terminate this agreement with 60 days written notice. Termination does not relieve either party of obligations accrued prior to the termination date.",
      score: 0.73,
    },
  ],
  "techcorp-handbook": [
    {
      chunkId: "chunk-onboarding-003",
      docId: "doc-onboarding-guide",
      docName: "Onboarding Guide.md",
      chunkIndex: 3,
      text: "New engineers get read access to all repositories on day one and write access after completing the security training module, usually by the end of week one.",
      score: 0.88,
    },
    {
      chunkId: "chunk-api-011",
      docId: "doc-api-style-guide",
      docName: "API Style Guide.md",
      chunkIndex: 11,
      text: "All public endpoints are versioned under /v{n}/ and must support at least one prior version for six months after a breaking change ships.",
      score: 0.9,
    },
    {
      chunkId: "chunk-api-019",
      docId: "doc-api-style-guide",
      docName: "API Style Guide.md",
      chunkIndex: 19,
      text: "Error responses use the shape { error: { code, message, details } }. The code field is a stable machine readable string, never a raw HTTP status.",
      score: 0.81,
    },
    {
      chunkId: "chunk-runbook-007",
      docId: "doc-incident-response-runbook",
      docName: "Incident Response Runbook.pdf",
      chunkIndex: 7,
      text: "Sev1 incidents page the on call engineer and the incident commander simultaneously. A status page update is required within 15 minutes of declaration.",
      score: 0.84,
    },
  ],
};
