"""Correctness of the benchmark orchestration itself — not performance
numbers (those are environment-dependent), just that the mechanics work:
ingestion lands the right chunk count, latency stats are well-formed, salted
facts are actually retrievable, and the throwaway tenant is fully cleaned up
even though the real cold-rebuild step (which needs a real Qdrant server,
since ":memory:" state is process-local) is swapped for an in-process fake.
"""

import time

import pytest
from qdrant_client import QdrantClient

from app.qdrant_client import COLLECTION_NAME, ensure_collection
from app.retrieval import keyword
from benchmarks.run import render_markdown, run_benchmark


@pytest.fixture
def qdrant_client():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    return client


def _fake_cold_rebuild(tenant_id, client):
    start = time.perf_counter()
    keyword.rebuild_from_qdrant(tenant_id, client=client)
    elapsed = time.perf_counter() - start
    return elapsed, 12_345  # fabricated RSS delta; real measurement needs a real server + subprocess


def _run(qdrant_client, fake_embed_fn, **overrides):
    kwargs = {
        "n_docs": 5,
        "client": qdrant_client,
        "embed_fn": fake_embed_fn,
        "n_queries": 10,
        "measure_cold_rebuild": _fake_cold_rebuild,
    }
    kwargs.update(overrides)
    return run_benchmark(**kwargs)


def test_ingests_expected_chunk_count(qdrant_client, fake_embed_fn):
    # Cleanup runs in a `finally`, so Qdrant is already empty by the time
    # this returns — n_chunks and the hit-rate test are what prove real
    # content landed and was retrievable during the run.
    result = _run(qdrant_client, fake_embed_fn)

    assert result.n_docs == 5
    assert result.n_chunks > 0


def test_reports_well_formed_latency_percentiles(qdrant_client, fake_embed_fn):
    result = _run(qdrant_client, fake_embed_fn)

    assert result.latency_p50_ms >= 0
    assert result.latency_p95_ms >= result.latency_p50_ms
    assert result.latency_max_ms >= result.latency_mean_ms >= result.latency_min_ms


def test_finds_the_salted_facts(qdrant_client, fake_embed_fn):
    result = _run(qdrant_client, fake_embed_fn)

    assert result.hit_rate > 0


def test_cleans_up_the_tenant_on_success(qdrant_client, fake_embed_fn):
    result = _run(qdrant_client, fake_embed_fn)

    assert qdrant_client.count(collection_name=COLLECTION_NAME).count == 0
    assert keyword.chunk_count(result.tenant_id) == 0


def test_cleans_up_the_tenant_even_if_a_query_raises(qdrant_client, fake_embed_fn):
    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure mid-benchmark")

    with pytest.raises(RuntimeError):
        run_benchmark(
            n_docs=5,
            client=qdrant_client,
            embed_fn=fake_embed_fn,
            n_queries=10,
            measure_cold_rebuild=_boom,
        )

    assert qdrant_client.count(collection_name=COLLECTION_NAME).count == 0


def test_render_markdown_includes_key_metrics(qdrant_client, fake_embed_fn):
    result = _run(qdrant_client, fake_embed_fn)

    table = render_markdown([result])

    assert "docs/sec" in table
    assert "p50" in table
    assert "p95" in table
    assert str(result.n_docs) in table


def test_batching_produces_the_same_result_as_a_single_batch(qdrant_client, fake_embed_fn):
    single_batch = _run(qdrant_client, fake_embed_fn, batch_size=1000)
    assert single_batch.n_chunks > 0
