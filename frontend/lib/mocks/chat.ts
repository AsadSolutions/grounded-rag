import { DEMO_CHUNKS } from "./fixtures";
import type { ChatEvent, RetrievedChunk, TraceEntry } from "@/lib/types";

const TOKEN_DELAY_MIN_MS = 20;
const TOKEN_DELAY_MAX_MS = 40;

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

function tokenize(answer: string): string[] {
  return answer.split(" ").map((word, i) => (i === 0 ? word : ` ${word}`));
}

async function* streamTokens(
  answer: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  for (const token of tokenize(answer)) {
    await sleep(
      TOKEN_DELAY_MIN_MS +
        Math.random() * (TOKEN_DELAY_MAX_MS - TOKEN_DELAY_MIN_MS),
      signal,
    );
    yield { type: "token", value: token };
  }
}

type Scenario = {
  match: (question: string) => boolean;
  answer: string;
  sources: RetrievedChunk[];
  trace: TraceEntry[];
  rewriteCount: number;
  regenerated: boolean;
  lowConfidence: boolean;
};

const includesAny = (question: string, needles: string[]) => {
  const q = question.toLowerCase();
  return needles.some((needle) => q.includes(needle));
};

const SCENARIOS: Record<string, Scenario[]> = {
  "acme-legal": [
    {
      match: (q) => includesAny(q, ["pto", "time off"]),
      answer:
        "Employees accrue 1.25 days of paid time off per month. Unused days carry over into the next calendar year up to a cap of 10 days; anything beyond that is forfeited on January 1st. [chunk-handbook-014]",
      sources: [DEMO_CHUNKS["acme-legal"][0]],
      trace: [
        {
          step: "retrieve",
          query: "pto",
          chunks: [],
        },
        { step: "grade", grades: [] },
        {
          step: "rewrite",
          attempt: 1,
          originalQuery: "pto",
          rewrittenQuery:
            "paid time off accrual, carryover, and forfeiture policy",
        },
        {
          step: "retrieve",
          query: "paid time off accrual, carryover, and forfeiture policy",
          chunks: [DEMO_CHUNKS["acme-legal"][0]],
        },
        {
          step: "grade",
          grades: [{ chunkId: "chunk-handbook-014", relevant: true }],
        },
        { step: "generate", attempt: 1 },
        { step: "groundedness_check", verdict: "grounded" },
      ],
      rewriteCount: 1,
      regenerated: false,
      lowConfidence: false,
    },
    {
      match: (q) => includesAny(q, ["salary", "ceo", "founder equity"]),
      answer:
        "Not found in the documents. The provided sources cover time off, data processing, and vendor contract terms, but do not mention compensation or equity figures.",
      sources: [],
      trace: [
        { step: "retrieve", query: "ceo salary", chunks: [] },
        { step: "grade", grades: [] },
        {
          step: "rewrite",
          attempt: 1,
          originalQuery: "ceo salary",
          rewrittenQuery: "executive compensation figures",
        },
        {
          step: "retrieve",
          query: "executive compensation figures",
          chunks: [],
        },
        { step: "grade", grades: [] },
        {
          step: "rewrite",
          attempt: 2,
          originalQuery: "executive compensation figures",
          rewrittenQuery: "founder or CEO pay, salary, or equity grant",
        },
        {
          step: "retrieve",
          query: "founder or CEO pay, salary, or equity grant",
          chunks: [],
        },
        { step: "grade", grades: [] },
        { step: "generate", attempt: 1 },
        {
          step: "groundedness_check",
          verdict: "not_grounded",
          reason: "No retrieved chunks support any compensation claim.",
        },
        { step: "generate", attempt: 2 },
        { step: "groundedness_check", verdict: "not_grounded" },
      ],
      rewriteCount: 2,
      regenerated: true,
      lowConfidence: true,
    },
  ],
  "techcorp-handbook": [
    {
      match: (q) =>
        includesAny(q, ["repository access", "repo access", "day one"]),
      answer:
        "New engineers receive read access to all repositories on day one, and write access after completing the security training module, typically by the end of week one. [chunk-onboarding-003]",
      sources: [DEMO_CHUNKS["techcorp-handbook"][0]],
      trace: [
        {
          step: "retrieve",
          query: "new engineer repository access timeline",
          chunks: [DEMO_CHUNKS["techcorp-handbook"][0]],
        },
        {
          step: "grade",
          grades: [{ chunkId: "chunk-onboarding-003", relevant: true }],
        },
        { step: "generate", attempt: 1 },
        { step: "groundedness_check", verdict: "grounded" },
      ],
      rewriteCount: 0,
      regenerated: false,
      lowConfidence: false,
    },
  ],
};

function genericScenario(tenantId: string, question: string): Scenario {
  const pool = DEMO_CHUNKS[tenantId] ?? [];
  const chunks = pool.slice(0, 2);
  const answer =
    chunks.length > 0
      ? `${chunks.map((c) => c.text).join(" ")} [${chunks.map((c) => c.chunkId).join(", ")}]`
      : "Not found in the documents.";
  return {
    match: () => true,
    answer,
    sources: chunks,
    trace: [
      { step: "retrieve", query: question, chunks },
      {
        step: "grade",
        grades: chunks.map((c) => ({ chunkId: c.chunkId, relevant: true })),
      },
      { step: "generate", attempt: 1 },
      {
        step: "groundedness_check",
        verdict: chunks.length > 0 ? "grounded" : "not_grounded",
      },
    ],
    rewriteCount: 0,
    regenerated: false,
    lowConfidence: chunks.length === 0,
  };
}

export async function* mockChat(
  tenantId: string,
  question: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  if (question.toLowerCase().includes("simulate error")) {
    yield {
      type: "error",
      message: "Mock: simulated backend failure while generating an answer.",
    };
    return;
  }

  const scenario =
    (SCENARIOS[tenantId] ?? []).find((s) => s.match(question)) ??
    genericScenario(tenantId, question);

  yield* streamTokens(scenario.answer, signal);
  yield { type: "sources", chunks: scenario.sources };
  yield {
    type: "trace",
    trace: {
      steps: scenario.trace,
      rewriteCount: scenario.rewriteCount,
      regenerated: scenario.regenerated,
      lowConfidence: scenario.lowConfidence,
    },
  };
}
