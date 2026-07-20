"use client";

import { useState, type ReactNode } from "react";
import { Drawer } from "@/components/ui/drawer";
import { Badge } from "@/components/ui/badge";
import { splitCitations, type CitationSource } from "@/lib/citations";
import type { ChatTrace, TraceEntry } from "@/lib/types";

function collectCitationSources(steps: TraceEntry[]): CitationSource[] {
  const byId = new Map<string, string>();
  for (const step of steps) {
    if (step.step === "retrieve") {
      for (const chunk of step.chunks) byId.set(chunk.chunkId, chunk.docName);
    }
    if (step.step === "grade") {
      for (const grade of step.grades) byId.set(grade.chunkId, grade.docName);
    }
  }
  return [...byId.entries()].map(([chunkId, docName]) => ({ chunkId, docName }));
}

export function TraceDrawer({
  open,
  onClose,
  trace,
}: {
  open: boolean;
  onClose: () => void;
  trace: ChatTrace | null;
}) {
  const citationSources = trace ? collectCitationSources(trace.steps) : [];

  return (
    <Drawer open={open} onClose={onClose} title="Reasoning">
      {trace ? (
        <ol className="flex flex-col gap-5">
          {trace.steps.map((step, index) => (
            <li key={index} className="relative border-l-2 border-border pl-4">
              <span
                className="absolute -left-[5px] top-1 size-2 rounded-full border-2 border-surface bg-border"
                aria-hidden="true"
              />
              <TraceStep step={step} citationSources={citationSources} />
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-body text-muted">No trace available.</p>
      )}
    </Drawer>
  );
}

function AnswerText({ text, citationSources }: { text: string; citationSources: CitationSource[] }) {
  const segments = splitCitations(text, citationSources);
  return (
    <p className="text-caption text-text">
      {segments.map((segment, index) =>
        segment.type === "text" ? (
          <span key={index}>{segment.value}</span>
        ) : (
          <span key={index} className="font-mono text-caption text-accent">
            [{segment.docNames.join(", ")}]
          </span>
        ),
      )}
    </p>
  );
}

function StepLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-eyebrow font-medium uppercase tracking-eyebrow text-muted">
      {children}
    </p>
  );
}

function TraceStep({
  step,
  citationSources,
}: {
  step: TraceEntry;
  citationSources: CitationSource[];
}) {
  switch (step.step) {
    case "retrieve":
      return (
        <div className="flex flex-col gap-2">
          <StepLabel>Retrieve</StepLabel>
          <p className="font-mono text-caption text-text">{step.query}</p>
          <ul className="flex flex-col gap-1">
            {step.chunks.map((chunk) => (
              <li key={chunk.chunkId} className="text-caption text-muted">
                {chunk.docName} · chunk {chunk.chunkIndex}
              </li>
            ))}
          </ul>
        </div>
      );
    case "grade":
      return <GradeStep step={step} />;
    case "rewrite":
      return (
        <div className="flex flex-col gap-2">
          <StepLabel>Rewrite (attempt {step.attempt})</StepLabel>
          <p className="font-mono text-caption text-muted line-through">
            {step.originalQuery}
          </p>
          <p className="font-mono text-caption text-text">
            {step.rewrittenQuery}
          </p>
        </div>
      );
    case "generate":
      return (
        <div className="flex flex-col gap-2">
          <StepLabel>
            {step.isRegeneration ? "Generate (regenerated)" : "Generate"}
          </StepLabel>
          <AnswerText text={step.answer} citationSources={citationSources} />
        </div>
      );
    case "groundedness_check":
      return (
        <div className="flex flex-col gap-2">
          <StepLabel>Groundedness check</StepLabel>
          <Badge variant={step.verdict === "grounded" ? "ok" : "warn"}>
            {step.verdict === "grounded" ? "Grounded" : "Low confidence"}
          </Badge>
          {step.reason && (
            <AnswerText text={step.reason} citationSources={citationSources} />
          )}
        </div>
      );
    case "log":
      return (
        <div className="flex flex-col gap-2">
          <StepLabel>{step.node}</StepLabel>
          <p className="text-caption text-text">{step.message}</p>
        </div>
      );
  }
}

function GradeStep({ step }: { step: Extract<TraceEntry, { step: "grade" }> }) {
  const [expanded, setExpanded] = useState(false);
  const total = step.grades.length;
  const relevantCount = step.grades.filter((grade) => grade.relevant).length;

  return (
    <div className="flex flex-col gap-2">
      <StepLabel>Grade</StepLabel>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        className="flex w-fit cursor-pointer items-center gap-1.5 text-caption transition-colors duration-150 ease-out hover:text-text"
      >
        <ChevronIcon
          className={`text-muted transition-transform duration-150 ease-out ${expanded ? "rotate-180" : ""}`}
        />
        <span className="text-muted">{total} retrieved</span>
        <span className="text-muted">·</span>
        <span className="text-ok">{relevantCount} relevant</span>
      </button>
      {expanded && (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {step.grades.map((grade) => (
            <span
              key={grade.chunkId}
              className={`rounded-button bg-surface-2 px-2 py-1 text-caption ${
                grade.relevant ? "text-ok" : "text-muted line-through"
              }`}
            >
              {grade.docName} · chunk {grade.chunkIndex}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ChevronIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path
        d="M4 6l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
