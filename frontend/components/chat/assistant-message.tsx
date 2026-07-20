import { splitCitations } from "@/lib/citations";
import type { RetrievedChunk } from "@/lib/types";

export function AssistantMessage({
  content,
  streaming,
  stage,
  sources = [],
}: {
  content: string;
  streaming: boolean;
  stage?: string | null;
  sources?: RetrievedChunk[];
}) {
  if (streaming && content === "" && stage) {
    return (
      <p className="animate-pulse text-caption text-muted" aria-live="polite">
        {stage}…
      </p>
    );
  }

  const segments = splitCitations(content, sources);

  return (
    <p className="whitespace-pre-wrap text-body leading-reading text-text">
      {segments.map((segment, index) =>
        segment.type === "text" ? (
          <span key={index}>{segment.value}</span>
        ) : (
          <span
            key={index}
            data-chunk-ids={segment.chunkIds.join(",")}
            className="font-mono text-caption text-accent"
          >
            [{segment.docNames.join(", ")}]
          </span>
        ),
      )}
      {streaming && (
        <span
          className="ml-0.5 inline-block h-[1em] w-0.5 animate-pulse bg-accent align-text-bottom"
          aria-hidden="true"
        />
      )}
    </p>
  );
}
