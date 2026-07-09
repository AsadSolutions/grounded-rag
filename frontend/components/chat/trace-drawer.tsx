import { Drawer } from "@/components/ui/drawer";
import { Badge } from "@/components/ui/badge";
import type { ChatTrace, TraceEntry } from "@/lib/types";

export function TraceDrawer({
  open,
  onClose,
  trace,
}: {
  open: boolean;
  onClose: () => void;
  trace: ChatTrace | null;
}) {
  return (
    <Drawer open={open} onClose={onClose} title="Reasoning">
      {trace ? (
        <ol className="flex flex-col gap-4">
          {trace.steps.map((step, index) => (
            <li key={index} className="border-l-2 border-border pl-4">
              <TraceStep step={step} />
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-[15px] text-muted">No trace available.</p>
      )}
    </Drawer>
  );
}

function TraceStep({ step }: { step: TraceEntry }) {
  switch (step.step) {
    case "retrieve":
      return (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">
            Retrieve
          </p>
          <p className="font-mono text-[13px] text-text">{step.query}</p>
          <ul className="flex flex-col gap-1">
            {step.chunks.map((chunk) => (
              <li
                key={chunk.chunkId}
                className="font-mono text-[13px] text-muted"
              >
                {chunk.docName} · chunk {chunk.chunkIndex}
              </li>
            ))}
          </ul>
        </div>
      );
    case "grade":
      return (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">
            Grade
          </p>
          <div className="flex flex-wrap gap-1.5">
            {step.grades.map((grade) => (
              <span
                key={grade.chunkId}
                className={`rounded-button bg-surface-2 px-2 py-1 font-mono text-[13px] ${
                  grade.relevant ? "text-ok" : "text-muted line-through"
                }`}
              >
                {grade.chunkId}
              </span>
            ))}
          </div>
        </div>
      );
    case "rewrite":
      return (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">
            Rewrite (attempt {step.attempt})
          </p>
          <p className="font-mono text-[13px] text-muted line-through">
            {step.originalQuery}
          </p>
          <p className="font-mono text-[13px] text-text">
            {step.rewrittenQuery}
          </p>
        </div>
      );
    case "generate":
      return (
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">
          Generate (attempt {step.attempt})
        </p>
      );
    case "groundedness_check":
      return (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">
            Groundedness check
          </p>
          <Badge variant={step.verdict === "grounded" ? "ok" : "danger"}>
            {step.verdict === "grounded" ? "Grounded" : "Not grounded"}
          </Badge>
          {step.reason && (
            <p className="text-[13px] text-muted">{step.reason}</p>
          )}
        </div>
      );
  }
}
