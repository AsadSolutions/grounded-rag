import type { Document } from "@/lib/types";

const PROGRESS_STAGES = [0, 30, 65, 100];
const STAGE_DELAY_MS = 250;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let nextChunkCount = 12;

export async function mockUploadDocument(
  tenantId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<Document> {
  for (const pct of PROGRESS_STAGES) {
    await sleep(STAGE_DELAY_MS);
    onProgress?.(pct);
  }

  const chunkCount = nextChunkCount;
  nextChunkCount += 6;

  return {
    id: `doc-upload-${Date.now()}`,
    tenantId,
    name: file.name,
    chunkCount,
    uploadedAt: new Date().toISOString(),
  };
}
