"use client";

import { useEffect, useRef, useState } from "react";
import { useChatThreads } from "@/lib/chat-threads-context";
import { useChatStream } from "@/lib/useChatStream";
import { useSettings } from "@/lib/settings-context";
import { MessageBubble } from "./message-bubble";
import { AssistantMessage } from "./assistant-message";
import { AnswerFooter } from "./answer-footer";
import { TraceDrawer } from "./trace-drawer";
import { ChatInput } from "./chat-input";
import { Badge } from "@/components/ui/badge";
import type { ChatMessage } from "@/lib/threads";
import type { ChatTrace } from "@/lib/types";

export function ChatPanel({ tenantId }: { tenantId: string }) {
  const { activeThread, startThread, appendMessage, setIsStreamingActive } =
    useChatThreads();
  const { settings } = useSettings();
  const stream = useChatStream();
  const [question, setQuestion] = useState("");
  const [drawerTrace, setDrawerTrace] = useState<ChatTrace | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pendingRef = useRef<{ threadId: string; messageId: string } | null>(
    null,
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [activeThread?.messages.length, stream.answer]);

  useEffect(() => {
    setIsStreamingActive(stream.status === "streaming");
  }, [stream.status, setIsStreamingActive]);

  useEffect(() => {
    if (stream.status !== "done" && stream.status !== "error") return;
    const pending = pendingRef.current;
    if (!pending) return;
    pendingRef.current = null;
    const { threadId, messageId } = pending;

    const assistantMessage: ChatMessage =
      stream.status === "error"
        ? {
            id: messageId,
            role: "assistant",
            content: "",
            sources: [],
            trace: {
              steps: [],
              rewriteCount: 0,
              regenerated: false,
              lowConfidence: true,
              skippedPipeline: true,
            },
            error: stream.error ?? "Unknown streaming error.",
          }
        : {
            id: messageId,
            role: "assistant",
            content: stream.answer,
            sources: stream.sources,
            trace: stream.trace ?? {
              steps: [],
              rewriteCount: 0,
              regenerated: false,
              lowConfidence: true,
              skippedPipeline: true,
            },
          };

    appendMessage(threadId, assistantMessage);

    if (stream.status === "done" && settings.showReasoningByDefault) {
      setDrawerTrace(stream.trace);
      setDrawerOpen(true);
    }
  }, [stream.status]);

  function handleSubmit() {
    const trimmed = question.trim();
    if (!trimmed || stream.status === "streaming") return;

    const thread = activeThread ?? startThread(trimmed);
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    appendMessage(thread.id, userMessage);

    pendingRef.current = {
      threadId: thread.id,
      messageId: crypto.randomUUID(),
    };
    setQuestion("");
    stream.start(tenantId, trimmed, { buffered: !settings.streaming });
  }

  const messages = activeThread?.messages ?? [];
  const isStreamingActive = stream.status === "streaming";
  const isCompact = settings.density === "compact";

  return (
    <div className="flex h-full min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto">
        <div
          className={`mx-auto flex w-full max-w-content flex-col px-6 ${
            isCompact ? "gap-4 py-6" : "gap-6 py-8"
          }`}
        >
          {messages.length === 0 && !isStreamingActive ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 py-24 text-center">
              <p className="font-serif text-xl text-text">
                Ask your documents anything.
              </p>
            </div>
          ) : (
            messages.map((message) =>
              message.role === "user" ? (
                <MessageBubble key={message.id} content={message.content} />
              ) : (
                <div
                  key={message.id}
                  className="animate-fade-slide-in flex flex-col gap-1"
                >
                  {message.error ? (
                    <Badge variant="danger">{message.error}</Badge>
                  ) : (
                    <>
                      <AssistantMessage
                        content={message.content}
                        streaming={false}
                      />
                      {!message.trace.skippedPipeline && (
                        <AnswerFooter
                          sourceCount={message.sources.length}
                          onShowReasoning={() => {
                            setDrawerTrace(message.trace);
                            setDrawerOpen(true);
                          }}
                        />
                      )}
                    </>
                  )}
                </div>
              ),
            )
          )}
          {isStreamingActive && (
            <div className="animate-fade-slide-in">
              {stream.error ? (
                <Badge variant="danger">{stream.error}</Badge>
              ) : (
                <AssistantMessage
                  content={stream.answer}
                  streaming
                  stage={stream.stage}
                />
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <div className={`px-6 ${isCompact ? "py-3" : "py-4"}`}>
        <div className="mx-auto w-full max-w-content">
          <ChatInput
            value={question}
            onChange={setQuestion}
            onSubmit={handleSubmit}
            disabled={isStreamingActive}
            placeholder="Ask a question..."
          />
        </div>
      </div>
      <TraceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        trace={drawerTrace}
      />
    </div>
  );
}
