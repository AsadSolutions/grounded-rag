import { AssistantMessage } from "./assistant-message";
import { AnswerFooter } from "./answer-footer";
import type { ChatMessage } from "@/lib/threads";

export function AssistantAnswer({
  message,
  onShowReasoning,
}: {
  message: Extract<ChatMessage, { role: "assistant" }>;
  onShowReasoning: () => void;
}) {
  return (
    <>
      <AssistantMessage
        content={message.content}
        streaming={false}
        sources={message.sources}
      />
      {!message.trace.skippedPipeline && (
        <AnswerFooter
          sourceCount={message.sources.length}
          onShowReasoning={onShowReasoning}
        />
      )}
    </>
  );
}
