export function AssistantMessage({
  content,
  streaming,
}: {
  content: string;
  streaming: boolean;
}) {
  return (
    <p className="whitespace-pre-wrap text-[15px] leading-[1.6] text-text">
      {content}
      {streaming && (
        <span
          className="ml-0.5 inline-block h-[1em] w-[2px] animate-pulse bg-accent align-text-bottom"
          aria-hidden="true"
        />
      )}
    </p>
  );
}
