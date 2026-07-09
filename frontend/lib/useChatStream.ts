"use client";

import { useCallback, useRef, useState } from "react";
import { chat } from "@/lib/api";
import type { ChatTrace, RetrievedChunk } from "@/lib/types";

export type ChatStreamStatus = "idle" | "streaming" | "done" | "error";

export type ChatStreamResult = {
  status: ChatStreamStatus;
  answer: string;
  sources: RetrievedChunk[];
  trace: ChatTrace | null;
  error: string | null;
  start: (
    tenantId: string,
    question: string,
    options?: { buffered?: boolean },
  ) => void;
  stop: () => void;
};

export function useChatStream(): ChatStreamResult {
  const [status, setStatus] = useState<ChatStreamStatus>("idle");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<RetrievedChunk[]>([]);
  const [trace, setTrace] = useState<ChatTrace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const start = useCallback(
    (tenantId: string, question: string, options?: { buffered?: boolean }) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setStatus("streaming");
      setAnswer("");
      setSources([]);
      setTrace(null);
      setError(null);

      const buffered = options?.buffered ?? false;

      (async () => {
        let buffer = "";
        try {
          for await (const event of chat(
            tenantId,
            question,
            controller.signal,
          )) {
            switch (event.type) {
              case "token":
                buffer += event.value;
                if (!buffered) setAnswer(buffer);
                break;
              case "sources":
                setSources(event.chunks);
                break;
              case "trace":
                setTrace(event.trace);
                break;
              case "error":
                setError(event.message);
                setStatus("error");
                return;
            }
          }
          if (buffered) setAnswer(buffer);
          setStatus("done");
        } catch (err) {
          if (
            controller.signal.aborted ||
            (err instanceof DOMException && err.name === "AbortError")
          ) {
            return;
          }
          setError(
            err instanceof Error ? err.message : "Unknown streaming error.",
          );
          setStatus("error");
        }
      })();
    },
    [],
  );

  return { status, answer, sources, trace, error, start, stop };
}
