export function MessageBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-lg border border-border bg-bg px-5 py-1.5 text-sm leading-reading text-text">
        {content}
      </div>
    </div>
  );
}
