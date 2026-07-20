export default function Loading() {
  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex-1 px-6 py-8">
        <div className="mx-auto flex w-full max-w-content flex-col gap-4">
          <div className="h-4 w-2/3 animate-pulse rounded-card bg-surface-2" />
          <div className="h-4 w-1/2 animate-pulse rounded-card bg-surface-2" />
        </div>
      </div>
      <div className="hidden w-docs-panel shrink-0 border-l border-border bg-surface p-5 lg:block">
        <div className="h-4 w-24 animate-pulse rounded-card bg-surface-2" />
      </div>
    </div>
  );
}
