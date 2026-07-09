export function AnswerFooter({
  sourceCount,
  onShowReasoning,
}: {
  sourceCount: number;
  onShowReasoning: () => void;
}) {
  return (
    <div className="mt-2 flex items-center gap-3 text-[13px] text-muted">
      <span>
        {sourceCount} {sourceCount === 1 ? "source" : "sources"}
      </span>
      <button
        onClick={onShowReasoning}
        className="cursor-pointer text-accent underline decoration-border underline-offset-4 transition-colors duration-150 ease-out hover:decoration-accent"
      >
        Show reasoning
      </button>
    </div>
  );
}
