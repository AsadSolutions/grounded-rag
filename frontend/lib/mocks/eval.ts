import type { EvalResults } from "@/lib/types";

export const MOCK_EVAL_RESULTS: EvalResults = {
  generatedAt: "2026-06-15T12:00:00.000Z",
  sample: true,
  metrics: [
    {
      name: "Retrieval hit rate",
      withCorrection: 0.93,
      withoutCorrection: 0.78,
      delta: 0.15,
    },
    {
      name: "Groundedness rate",
      withCorrection: 0.96,
      withoutCorrection: 0.84,
      delta: 0.12,
    },
    {
      name: "Not-found honesty",
      withCorrection: 1.0,
      withoutCorrection: 0.6,
      delta: 0.4,
    },
  ],
};
