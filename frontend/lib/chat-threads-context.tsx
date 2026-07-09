"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  deleteThread as deleteThreadStorage,
  listThreads,
  renameThread as renameThreadStorage,
  saveThread,
  type ChatMessage,
  type ChatThread,
} from "@/lib/threads";

const CHAT_QUERY_PARAM = "chat";

type ChatThreadsContextValue = {
  tenantId: string;
  threads: ChatThread[];
  activeThreadId: string | null;
  activeThread: ChatThread | null;
  selectThread: (threadId: string | null) => void;
  startThread: (firstQuestion: string) => ChatThread;
  appendMessage: (threadId: string, message: ChatMessage) => void;
  renameThread: (threadId: string, title: string) => void;
  deleteThread: (threadId: string) => void;
  isStreamingActive: boolean;
  setIsStreamingActive: (active: boolean) => void;
};

const ChatThreadsContext = createContext<ChatThreadsContextValue | null>(null);

const TITLE_MAX_LENGTH = 60;

export function ChatThreadsProvider({
  tenantId,
  children,
}: {
  tenantId: string;
  children: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isStreamingActive, setIsStreamingActive] = useState(false);

  useEffect(() => {
    const loaded = listThreads(tenantId);
    setThreads(loaded);
    const urlThreadId = searchParams.get(CHAT_QUERY_PARAM);
    setActiveThreadId(
      urlThreadId && loaded.some((t) => t.id === urlThreadId)
        ? urlThreadId
        : null,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  const syncUrl = useCallback(
    (threadId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (threadId) params.set(CHAT_QUERY_PARAM, threadId);
      else params.delete(CHAT_QUERY_PARAM);
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, {
        scroll: false,
      });
    },
    [pathname, router, searchParams],
  );

  const selectThread = useCallback(
    (threadId: string | null) => {
      setActiveThreadId(threadId);
      syncUrl(threadId);
    },
    [syncUrl],
  );

  const startThread = useCallback(
    (firstQuestion: string): ChatThread => {
      const now = new Date().toISOString();
      const title =
        firstQuestion.length > TITLE_MAX_LENGTH
          ? `${firstQuestion.slice(0, TITLE_MAX_LENGTH)}…`
          : firstQuestion;
      const thread: ChatThread = {
        id: crypto.randomUUID(),
        tenantId,
        title,
        createdAt: now,
        updatedAt: now,
        messages: [],
      };
      saveThread(tenantId, thread);
      setThreads((prev) => [thread, ...prev]);
      setActiveThreadId(thread.id);
      syncUrl(thread.id);
      return thread;
    },
    [tenantId, syncUrl],
  );

  const appendMessage = useCallback(
    (threadId: string, message: ChatMessage) => {
      setThreads((prev) =>
        prev.map((t) => {
          if (t.id !== threadId) return t;
          const existingIndex = t.messages.findIndex(
            (m) => m.id === message.id,
          );
          const messages =
            existingIndex === -1
              ? [...t.messages, message]
              : t.messages.map((m, i) => (i === existingIndex ? message : m));
          const updated = {
            ...t,
            messages,
            updatedAt: new Date().toISOString(),
          };
          saveThread(tenantId, updated);
          return updated;
        }),
      );
    },
    [tenantId],
  );

  const renameThreadValue = useCallback(
    (threadId: string, title: string) => {
      renameThreadStorage(tenantId, threadId, title);
      setThreads((prev) =>
        prev.map((t) => (t.id === threadId ? { ...t, title } : t)),
      );
    },
    [tenantId],
  );

  const deleteThreadValue = useCallback(
    (threadId: string) => {
      deleteThreadStorage(tenantId, threadId);
      setThreads((prev) => prev.filter((t) => t.id !== threadId));
      setActiveThreadId((current) => {
        if (current !== threadId) return current;
        syncUrl(null);
        return null;
      });
    },
    [tenantId, syncUrl],
  );

  const activeThread = threads.find((t) => t.id === activeThreadId) ?? null;

  return (
    <ChatThreadsContext.Provider
      value={{
        tenantId,
        threads,
        activeThreadId,
        activeThread,
        selectThread,
        startThread,
        appendMessage,
        renameThread: renameThreadValue,
        deleteThread: deleteThreadValue,
        isStreamingActive,
        setIsStreamingActive,
      }}
    >
      {children}
    </ChatThreadsContext.Provider>
  );
}

export function useChatThreads() {
  const ctx = useContext(ChatThreadsContext);
  if (!ctx)
    throw new Error("useChatThreads must be used within ChatThreadsProvider");
  return ctx;
}
