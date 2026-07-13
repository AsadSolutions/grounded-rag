export default function Loading() {
  return (
    <div className="flex flex-1 flex-col">
      <section className="flex flex-col items-center gap-8 px-6 pb-20 pt-24 text-center">
        <div className="h-20 w-96 max-w-full animate-pulse rounded-card bg-surface-2" />
        <div className="h-4 w-full max-w-xl animate-pulse rounded-card bg-surface-2" />
      </section>
      <section className="mx-auto flex w-full max-w-content flex-col gap-6 px-6 py-16">
        <div className="h-3 w-40 animate-pulse rounded-card bg-surface-2" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-card border border-border bg-surface-2"
            />
          ))}
        </div>
      </section>
    </div>
  );
}
