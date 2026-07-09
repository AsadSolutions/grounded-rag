# Scale Benchmark Results

Raw output of `python -m benchmarks.run --docs N` for N = 1000, 10000, 50000, run against
local Qdrant (docker compose, single node, default config, no tuning) on the developer
machine used for this project. Fake embedder (`benchmarks.fake_embedder.fast_fake_embed`,
random unit vectors, no OpenAI calls) used throughout — these numbers measure GroundedRAG's
own ingestion/BM25/Qdrant pipeline, not OpenAI API latency. 100 queries per run, sampled
against the salted fact ids actually ingested.

This file is a data record, not a claim. No conclusions here are asserted in the README —
that's an explicit decision for Asad to make from these numbers.

## Results table

| N docs | N chunks | Ingest docs/sec | Ingest chunks/sec | Cold BM25 rebuild (s) | Cold rebuild memory (MB) | Search p50 (ms) | Search p95 (ms) | Hit rate |
| ------ | -------- | --------------- | ----------------- | --------------------- | ------------------------ | --------------- | --------------- | -------- |
| 1000   | 2337     | 436.8           | 1020.8            | 0.197                 | 99.9                     | 5.44            | 8.23            | 100%     |
| 10000  | 23146    | 436.5           | 1010.2            | 1.897                 | 910.7                    | 34.50           | 41.65           | 100%     |
| 50000  | 115369   | 415.7           | 959.2             | 15.733                | 3813.8                   | 167.15          | 229.29          | 100%     |

## What degrades, and why (observed, not guessed)

- **Ingestion throughput holds roughly flat** (~416–437 docs/sec, ~960–1020 chunks/sec)
  across all three scales. This is expected: the benchmark's bulk ingest path
  (`benchmarks.run._bulk_ingest`) deliberately skips per-document BM25 maintenance — see
  the next point for why that matters.

- **Cold BM25 rebuild time scales worse than linearly**: ~50x more chunks (2337 → 115369)
  produced ~80x more rebuild time (0.197s → 15.733s). `rebuild_from_qdrant` pages through
  Qdrant (fixed now — see note below) and reconstructs a `rank_bm25.BM25Okapi` index from
  scratch every time; that constructor is O(corpus size) and this is a single-threaded,
  synchronous rebuild.

- **Cold rebuild memory scales roughly linearly with chunk count**, at a striking
  ~33–43 MB per 1000 chunks (99.9MB / 2337 chunks, 910.7MB / 23146 chunks, 3813.8MB /
  115369 chunks). At 115k chunks the in-process BM25 index + cached chunk texts for a
  _single tenant_ used **3.8GB of resident memory**. This is the concrete, measured case
  for the roadmap's own "After v1.0" item — replacing in-process BM25 with Qdrant sparse
  vectors — if any tenant is expected to reach tens of thousands of chunks.

- **Hybrid search latency degrades the most sharply of anything measured**: p50 went
  5.44ms → 34.50ms → 167.15ms (roughly 31x for a 50x increase in corpus size — close to
  linear, not the sub-linear scaling you'd want from an index). The suspect, based on the
  code path, is `keyword_search`'s per-query BM25 scoring: it calls
  `BM25Okapi.get_scores()` over the _entire_ tenant corpus, then does a Python-level
  `sorted()` over all of it, for every single query, regardless of k. That's O(corpus
  size) per query. Qdrant's own dense HNSW search is expected to be sub-linear and is not
  the likely cause; this wasn't independently isolated in this pass, so treat it as the
  most-likely explanation, not a confirmed root cause.

## A bug this benchmark surfaced and fixed before these numbers were taken

Building this benchmark surfaced a real pagination bug in `rebuild_from_qdrant`: it only
read a single Qdrant scroll page (previously hardcoded `limit=10_000`) and silently
dropped everything after it. A tenant with more than 10,000 chunks would have gotten an
incomplete BM25 index on every cold rebuild — including after every server restart, since
that's exactly when `rebuild_from_qdrant` runs. Fixed to page through the full result set
(`tests/test_bm25_rebuild_pagination.py`); the numbers above reflect the fixed version.

## Methodology notes and caveats

- **Hit rate at N=1000+ is 100%**, but was as low as 40-80% in small smoke tests (N=10).
  This is _not_ a retrieval-quality regression — the dense embedder used here produces
  meaningless random vectors (that's the point: it isolates the benchmark from OpenAI
  latency), so at small N, RRF fusion can occasionally let a randomly well-ranked
  irrelevant chunk edge out the correct one in the top-k blend. This is an artifact of
  the fake embedder, not evidence about real embedding quality, and it disappears at
  scale simply because more competing documents makes BM25's exact-match signal dominate
  the fusion more decisively.
- **Cold rebuild memory** is measured via peak RSS (`resource.getrusage`) in an isolated
  subprocess dedicated to only that operation, specifically so bulk-ingestion's own peak
  memory usage doesn't contaminate the reading. It's still an approximation — it includes
  Python/interpreter/import baseline overhead, not a pure data-structure size — but it's a
  real empirical measurement, not an estimate.
- **Ingestion in this benchmark is not the same code path as `POST /api/documents`.** The
  standard single-document upload (`app.ingest.pipeline.ingest_document`) rebuilds BM25
  incrementally on every call — fine for occasional uploads, but would reproduce the same
  O(n²)-ish cost this benchmark specifically avoided if used to bulk-load tens of
  thousands of documents back to back. `app.ingest.seed` already avoids this by rebuilding
  once per tenant at the end; any future bulk-import tool should do the same.
- Single run per N, not averaged — treat these as one honest sample, not a statistically
  tight estimate. Re-running would very likely shift the numbers by some percent, but is
  unlikely to change which trends are flat vs. degrading.
