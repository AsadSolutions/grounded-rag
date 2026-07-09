"""Scale benchmark: python -m benchmarks.run --docs N

Generates N synthetic documents, bulk-ingests them into a throwaway tenant,
measures ingestion throughput, a cold BM25 rebuild, its memory footprint,
and hybrid search latency over the salted facts — then deletes the tenant.

Ingestion here deliberately skips the per-document incremental BM25 rebuild
that app.ingest.pipeline.ingest_document performs on every upload. That
per-document rebuild is O(corpus size), so at bulk-load scale it would make
this benchmark's own "ingestion throughput" number reflect a quadratic
blowup rather than the ingest pipeline itself — and would make N=50000
impractically slow to even run. Instead BM25 is built once, cold, from
Qdrant afterward, which is exactly the "cold rebuild" metric below and
exactly the pattern app.ingest.seed already uses for bulk loading demo
tenants. This is itself a real finding, not just a benchmark convenience:
the standard single-document upload path does NOT scale to bulk imports of
many documents back-to-back without hitting this same cost.
"""

import argparse
import hashlib
import random
import secrets
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from app.config import get_settings
from app.ingest.chunk import chunk_text
from app.ingest.embed import embed_texts
from app.ingest.extract import extract_text
from app.qdrant_client import COLLECTION_NAME, ensure_collection
from app.retrieval import keyword
from app.retrieval.hybrid import hybrid_search
from benchmarks.fake_embedder import fast_fake_embed
from benchmarks.generate import generate_synthetic_documents

_BENCHMARKS_DIR = Path(__file__).resolve().parent


@dataclass
class BenchmarkResult:
    tenant_id: str
    n_docs: int
    n_chunks: int
    ingest_seconds: float
    docs_per_sec: float
    chunks_per_sec: float
    cold_rebuild_seconds: float
    cold_rebuild_rss_bytes: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_mean_ms: float
    latency_min_ms: float
    latency_max_ms: float
    hit_rate: float


def _bulk_ingest(documents, tenant_id, client, embed_fn, batch_size):
    """Extract+chunk+embed+upsert only — no BM25 maintenance. See module
    docstring for why that's deliberate here."""
    total_chunks = 0
    start = time.perf_counter()
    for batch_start in range(0, len(documents), batch_size):
        batch = documents[batch_start : batch_start + batch_size]
        batch_chunks = []
        for doc in batch:
            content_hash = hashlib.sha256(doc.content).hexdigest()
            text = extract_text(doc.doc_name, doc.content)
            doc_id = str(uuid.uuid4())
            batch_chunks.extend(
                chunk_text(text, tenant_id=tenant_id, doc_id=doc_id, doc_name=doc.doc_name, content_hash=content_hash)
            )
        if not batch_chunks:
            continue
        vectors = embed_fn([chunk.text for chunk in batch_chunks])
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(id=chunk.chunk_id, vector=vector, payload=chunk.model_dump())
                for chunk, vector in zip(batch_chunks, vectors)
            ],
        )
        total_chunks += len(batch_chunks)
    elapsed = time.perf_counter() - start
    return elapsed, total_chunks


def _measure_cold_rebuild_subprocess(tenant_id: str, qdrant_url: str) -> tuple[float, int]:
    result = subprocess.run(
        [sys.executable, "-m", "benchmarks._measure_rebuild_memory", tenant_id, qdrant_url],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(_BENCHMARKS_DIR.parent),
    )
    values = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            values[key] = value
    return float(values["REBUILD_SECONDS"]), int(values["RSS_DELTA_BYTES"])


def _cleanup(tenant_id: str, client: QdrantClient) -> None:
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]),
    )
    keyword.forget_tenant(tenant_id)


def run_benchmark(
    n_docs: int,
    *,
    qdrant_url: str | None = None,
    client: QdrantClient | None = None,
    embed_fn=fast_fake_embed,
    batch_size: int = 100,
    n_queries: int = 100,
    seed: int = 42,
    tenant_id: str | None = None,
    measure_cold_rebuild=None,
) -> BenchmarkResult:
    qdrant_url = qdrant_url or get_settings().qdrant_url
    client = client or QdrantClient(url=qdrant_url)
    ensure_collection(client)
    tenant_id = tenant_id or f"bench-{secrets.token_hex(4)}"
    measure_cold_rebuild = measure_cold_rebuild or (
        lambda tid, _client: _measure_cold_rebuild_subprocess(tid, qdrant_url)
    )

    try:
        documents = generate_synthetic_documents(n_docs, seed=seed)

        ingest_seconds, n_chunks = _bulk_ingest(documents, tenant_id, client, embed_fn, batch_size)
        docs_per_sec = n_docs / ingest_seconds if ingest_seconds > 0 else float("inf")
        chunks_per_sec = n_chunks / ingest_seconds if ingest_seconds > 0 else float("inf")

        keyword.forget_tenant(tenant_id) 
        cold_rebuild_seconds, cold_rebuild_rss_bytes = measure_cold_rebuild(tenant_id, client)

        keyword.rebuild_from_qdrant(tenant_id, client=client)

        rng = random.Random(seed)
        sampled_docs = rng.choices(documents, k=n_queries) if documents else []
        latencies_ms = []
        hits = 0
        for doc in sampled_docs:
            query_text = f"Tell me about fact identifier {doc.fact_id}"
            start = time.perf_counter()
            results = hybrid_search(tenant_id, query_text, k=6, client=client, embed_fn=embed_fn)
            latencies_ms.append((time.perf_counter() - start) * 1000)
            if any(doc.fact_id in r.text for r in results):
                hits += 1

        hit_rate = hits / len(sampled_docs) if sampled_docs else 0.0
        latencies_array = np.array(latencies_ms) if latencies_ms else np.array([0.0])

        return BenchmarkResult(
            tenant_id=tenant_id,
            n_docs=n_docs,
            n_chunks=n_chunks,
            ingest_seconds=ingest_seconds,
            docs_per_sec=docs_per_sec,
            chunks_per_sec=chunks_per_sec,
            cold_rebuild_seconds=cold_rebuild_seconds,
            cold_rebuild_rss_bytes=cold_rebuild_rss_bytes,
            latency_p50_ms=float(np.percentile(latencies_array, 50)),
            latency_p95_ms=float(np.percentile(latencies_array, 95)),
            latency_mean_ms=float(np.mean(latencies_array)),
            latency_min_ms=float(np.min(latencies_array)),
            latency_max_ms=float(np.max(latencies_array)),
            hit_rate=hit_rate,
        )
    finally:
        _cleanup(tenant_id, client)


def render_markdown(results: list[BenchmarkResult]) -> str:
    header = (
        "| N docs | N chunks | Ingest docs/sec | Ingest chunks/sec | "
        "Cold BM25 rebuild (s) | Cold rebuild memory (MB) | "
        "Search p50 (ms) | Search p95 (ms) | Hit rate |\n"
    )
    separator = "|---|---|---|---|---|---|---|---|---|\n"
    rows = "".join(
        f"| {r.n_docs} | {r.n_chunks} | {r.docs_per_sec:.1f} | {r.chunks_per_sec:.1f} | "
        f"{r.cold_rebuild_seconds:.3f} | {r.cold_rebuild_rss_bytes / (1024 * 1024):.1f} | "
        f"{r.latency_p50_ms:.2f} | {r.latency_p95_ms:.2f} | {r.hit_rate:.0%} |\n"
        for r in results
    )
    return header + separator + rows


def main() -> None:
    parser = argparse.ArgumentParser(description="GroundedRAG scale benchmark")
    parser.add_argument("--docs", type=int, required=True, help="Number of synthetic documents to ingest")
    parser.add_argument("--qdrant-url", default=None, help="Defaults to QDRANT_URL / config default")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--n-queries", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--real-embeddings",
        action="store_true",
        help="Use the real OpenAI embedder instead of the fast fake one (measures OpenAI latency too)",
    )
    parser.add_argument("--out", default=None, help="Optional file to write the markdown table to")
    args = parser.parse_args()

    embed_fn = embed_texts if args.real_embeddings else fast_fake_embed

    result = run_benchmark(
        n_docs=args.docs,
        qdrant_url=args.qdrant_url,
        embed_fn=embed_fn,
        batch_size=args.batch_size,
        n_queries=args.n_queries,
        seed=args.seed,
    )
    table = render_markdown([result])
    print(table)
    if args.out:
        Path(args.out).write_text(table)


if __name__ == "__main__":
    main()
