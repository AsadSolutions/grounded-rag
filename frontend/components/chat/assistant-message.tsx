export function AssistantMessage({
  content,
  streaming,
}: {
  content: string;
  streaming: boolean;
}) {
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
