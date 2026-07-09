# Evaluation Results

Aggregate of two independent full runs of `python -m app.eval.run` (45 golden questions each, unmodified code and golden set between runs) against the real OpenAI API and the seeded demo tenants — see `app/eval/golden_set.json` for the exact set and category tags. Each cell below is the mean across the two passes, with the min and max shown alongside so category-level noise is visible rather than hidden. Never hand-edited: regenerate by re-running the harness twice and re-aggregating if the golden set, prompts, or models change.

## Overall (2 passes, n=45 each)

| Metric             | Correction OFF (mean, min–max) | Correction ON (mean, min–max) | Delta (mean) |
| ------------------ | ------------------------------ | ----------------------------- | ------------ |
| Retrieval hit rate | 100.0% (100.0–100.0%)          | 98.6% (97.2–100.0%)           | -1.4pp       |
| Groundedness rate  | 96.7% (93.3–100.0%)            | 93.3% (91.1–95.6%)            | -3.3pp       |
| Not-found honesty  | 100.0% (100.0–100.0%)          | 100.0% (100.0–100.0%)         | +0.0pp       |

## Breakdown by category

### baseline (n=25)

| Metric             | Correction OFF (mean, min–max) | Correction ON (mean, min–max) | Delta (mean) |
| ------------------ | ------------------------------ | ----------------------------- | ------------ |
| Retrieval hit rate | 100.0% (100.0–100.0%)          | 100.0% (100.0–100.0%)         | +0.0pp       |
| Groundedness rate  | 98.0% (96.0–100.0%)            | 98.0% (96.0–100.0%)           | +0.0pp       |
| Not-found honesty  | 100.0% (100.0–100.0%)          | 100.0% (100.0–100.0%)         | +0.0pp       |

### rewrite_bait (n=6)

| Metric             | Correction OFF (mean, min–max) | Correction ON (mean, min–max) | Delta (mean) |
| ------------------ | ------------------------------ | ----------------------------- | ------------ |
| Retrieval hit rate | 100.0% (100.0–100.0%)          | 91.7% (83.3–100.0%)           | -8.3pp       |
| Groundedness rate  | 91.7% (83.3–100.0%)            | 83.3% (66.7–100.0%)           | -8.3pp       |
| Not-found honesty  | n/a                            | n/a                           | n/a          |

### multi_chunk (n=5)

| Metric             | Correction OFF (mean, min–max) | Correction ON (mean, min–max) | Delta (mean) |
| ------------------ | ------------------------------ | ----------------------------- | ------------ |
| Retrieval hit rate | 100.0% (100.0–100.0%)          | 100.0% (100.0–100.0%)         | +0.0pp       |
| Groundedness rate  | 100.0% (100.0–100.0%)          | 90.0% (80.0–100.0%)           | -10.0pp      |
| Not-found honesty  | n/a                            | n/a                           | n/a          |

### distractor_trap (n=5)

| Metric             | Correction OFF (mean, min–max) | Correction ON (mean, min–max) | Delta (mean) |
| ------------------ | ------------------------------ | ----------------------------- | ------------ |
| Retrieval hit rate | 100.0% (100.0–100.0%)          | 100.0% (100.0–100.0%)         | +0.0pp       |
| Groundedness rate  | 100.0% (100.0–100.0%)          | 90.0% (80.0–100.0%)           | -10.0pp      |
| Not-found honesty  | n/a                            | n/a                           | n/a          |

### near_miss_unanswerable (n=4)

| Metric             | Correction OFF (mean, min–max) | Correction ON (mean, min–max) | Delta (mean) |
| ------------------ | ------------------------------ | ----------------------------- | ------------ |
| Retrieval hit rate | n/a                            | n/a                           | n/a          |
| Groundedness rate  | 87.5% (75.0–100.0%)            | 87.5% (75.0–100.0%)           | +0.0pp       |
| Not-found honesty  | 100.0% (100.0–100.0%)          | 100.0% (100.0–100.0%)         | +0.0pp       |

### Judge agreement (independent eval judge vs. the pipeline's internal groundedness check, correction ON only)

- Pass 1: 39/45 (86.7%)
- Pass 2: 37/45 (82.2%)
- Combined: 76/90 (84.4%)

## Limitations and Findings

**Category sizes of 5–6 produce noisy deltas.** `rewrite_bait`, `multi_chunk`, and `distractor_trap` each contain only 5–6 questions, so a single question flipping outcome moves the category rate by 17–20 points. Running the harness twice against identical code produced a 33.3pp swing in `rewrite_bait` groundedness rate under correction ON alone (66.7% in pass 1 vs. 100.0% in pass 2), and 20–25pp swings in `multi_chunk`, `distractor_trap`, and `near_miss_unanswerable`. The 25-question `baseline` category, by contrast, moved only 4pp between passes. Category-level deltas below roughly 20pp in the small categories are not distinguishable from run-to-run noise at this sample size; only the `baseline` category and the overall aggregate are stable enough to draw a directional conclusion from a single run.

**Two multi-hop failure mechanisms were diagnosed and are documented in `app/eval/transcripts/`:**

1. _Generation-level figure substitution_ (`multi-02.json`, correction ON): the correct chunk was retrieved and graded relevant, but the model answered "30 days in advance" for a PTO request when the source states "15 business days." The same retrieved chunk also contains an unrelated leave-of-absence clause requiring "30 days" notice, and the model substituted that figure in — and repeated the identical wrong figure even after the internal groundedness check forced a regeneration. This is a generation failure, not a retrieval failure.
2. _Grader cross-attribution between overlapping chunks_ (`multi-03.json`, correction ON): the independent eval judge flagged "the General Counsel's office has sole authority to lift a hold" as unsupported, even though that exact sentence appears verbatim in two overlapping, windowed chunks that were both retrieved and both graded relevant. The duplicate chunk boundaries appear to have confused the judge's claim-to-source attribution, producing a false-unsupported verdict on a claim the sources state twice. In the same transcript, a second claim in the same answer ("immediately" vs. the source's "24 hours") was a genuine generation-level substitution, correctly caught by the judge — illustrating that the two failure mechanisms can co-occur in a single answer and must be told apart by reading the transcript, not inferred from the judge verdict alone.

**The internal groundedness check rework raised judge agreement from 60% to 82%.** The pipeline's internal `check_groundedness_llm` previously asked the model to emit `grounded` directly alongside its claim extraction; because structured-output fields decode in schema order, the model committed to a verdict before doing the extraction meant to justify it, which periodically produced self-contradictory output (`grounded=false` with an empty unsupported-claims list, or vice versa) and put agreement with the independent eval judge at roughly 60%. Deriving `grounded` in code from whether `unsupported_claims` is empty (rather than asking the model for it directly) removed that structural contradiction; agreement between the internal check and the independent judge in this run measured 86.7% (pass 1) and 82.2% (pass 2), a combined 84.4%.
