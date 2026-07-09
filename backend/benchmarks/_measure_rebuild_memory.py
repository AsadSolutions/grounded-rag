"""Runs the cold BM25 rebuild for one tenant in an isolated subprocess.

Measuring memory footprint accurately from inside the same long-running
process that just did bulk ingestion is misleading: `resource.getrusage`
reports *peak* RSS, which ingestion itself may have already pushed higher
than the rebuild alone would ever need, understating the rebuild's real
cost. Running it as a fresh subprocess whose only job is the rebuild gives a
peak-RSS reading that actually reflects that operation.

Only works against a real Qdrant server (a URL, not ":memory:") since
in-memory Qdrant state is process-local and wouldn't be visible here.

Usage: python -m benchmarks._measure_rebuild_memory <tenant_id> <qdrant_url>
Prints REBUILD_SECONDS=..., RSS_DELTA_BYTES=..., CHUNK_COUNT=... to stdout.
"""

import gc
import resource
import sys
import time


def _rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def main() -> None:
    tenant_id = sys.argv[1]
    qdrant_url = sys.argv[2]

    from qdrant_client import QdrantClient

    from app.retrieval import keyword

    client = QdrantClient(url=qdrant_url)

    gc.collect()
    rss_before = _rss_bytes()

    start = time.perf_counter()
    keyword.rebuild_from_qdrant(tenant_id, client=client)
    elapsed = time.perf_counter() - start

    gc.collect()
    rss_after = _rss_bytes()

    print(f"REBUILD_SECONDS={elapsed}")
    print(f"RSS_DELTA_BYTES={max(rss_after - rss_before, 0)}")
    print(f"CHUNK_COUNT={keyword.chunk_count(tenant_id)}")


if __name__ == "__main__":
    main()
