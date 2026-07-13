export function AssistantMessage({
  content,
  streaming,
  stage,
}: {
  content: string;
  streaming: boolean;
  stage?: string | null;
}) {
  if (streaming && content === "" && stage) {
    return (
      <p className="animate-pulse text-caption text-muted" aria-live="polite">
        {stage}…
      </p>
    );
  }

  return (
    <p className="whitespace-pre-wrap text-body leading-reading text-text">
      {content}
      {streaming && (
        <span
          className="ml-0.5 inline-block h-[1em] w-0.5 animate-pulse bg-accent align-text-bottom"
          aria-hidden="true"
        />
      )}
    </p>
  );
}
