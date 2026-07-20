export default function Loading() {
  return (
    <div className="mx-auto flex w-full max-w-content flex-col gap-8 overflow-y-auto px-6 py-16">
      <div className="h-8 w-32 animate-pulse rounded-card bg-surface-2" />
      <div className="h-4 w-full max-w-evals-copy animate-pulse rounded-card bg-surface-2" />
      <div className="overflow-hidden rounded-card border border-border bg-surface">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="flex items-center gap-4 border-b border-border px-5 py-4 last:border-b-0"
          >
            <div className="h-4 flex-1 animate-pulse rounded-card bg-surface-2" />
            <div className="h-4 w-16 animate-pulse rounded-card bg-surface-2" />
            <div className="h-4 w-16 animate-pulse rounded-card bg-surface-2" />
            <div className="h-4 w-12 animate-pulse rounded-card bg-surface-2" />
          </div>
        ))}
      </div>
    </div>
  );
}
