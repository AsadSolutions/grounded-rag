import type { ChatTrace, RetrievedChunk } from "@/lib/types";

export type ChatMessage =
  | { id: string; role: "user"; content: string }
  | {
      id: string;
      role: "assistant";
      content: string;
      sources: RetrievedChunk[];
      trace: ChatTrace;
      error?: string;
    };

export type ChatThread = {
  id: string;
  tenantId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
};

function storageKey(tenantId: string): string {
  return `groundedrag-threads-${tenantId}`;
}

function lastActiveThreadKey(tenantId: string): string {
  return `groundedrag-last-thread-${tenantId}`;
}

export function getLastActiveThreadId(tenantId: string): string | null {
  return window.localStorage.getItem(lastActiveThreadKey(tenantId));
}

export function setLastActiveThreadId(
  tenantId: string,
  threadId: string | null,
): void {
  if (threadId) {
    window.localStorage.setItem(lastActiveThreadKey(tenantId), threadId);
  } else {
    window.localStorage.removeItem(lastActiveThreadKey(tenantId));
  }
}

export function listThreads(tenantId: string): ChatThread[] {
  const raw = window.localStorage.getItem(storageKey(tenantId));
  if (!raw) return [];
  try {
    return JSON.parse(raw) as ChatThread[];
  } catch {
    console.error(`Corrupt thread data for tenant ${tenantId}, resetting.`);
    return [];
  }
}

function persist(tenantId: string, threads: ChatThread[]): void {
  window.localStorage.setItem(storageKey(tenantId), JSON.stringify(threads));
}

export function saveThread(tenantId: string, thread: ChatThread): void {
  const threads = listThreads(tenantId);
  const index = threads.findIndex((t) => t.id === thread.id);
  const next =
    index === -1
      ? [thread, ...threads]
      : threads.map((t, i) => (i === index ? thread : t));
  persist(tenantId, next);
}

export function renameThread(
  tenantId: string,
  threadId: string,
  title: string,
): void {
  const threads = listThreads(tenantId).map((t) =>
    t.id === threadId ? { ...t, title } : t,
  );
  persist(tenantId, threads);
}

export function deleteThread(tenantId: string, threadId: string): void {
  persist(
    tenantId,
    listThreads(tenantId).filter((t) => t.id !== threadId),
  );
}

export function clearThreads(tenantId: string): void {
  window.localStorage.removeItem(storageKey(tenantId));
}
