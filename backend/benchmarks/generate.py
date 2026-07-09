"""Synthetic document generation for the scale benchmark.

Each document is salted with a unique fact id (appearing near both the start
and end of the document, so it survives chunking regardless of chunk count)
so retrieval latency queries can target real, checkable content instead of
generic filler.
"""

import random
from dataclasses import dataclass

MIN_WORDS = 300
MAX_WORDS = 2000

_WORD_BANK = [
    "quarterly",
    "system",
    "policy",
    "workflow",
    "customer",
    "invoice",
    "report",
    "server",
    "database",
    "engineering",
    "release",
    "meeting",
    "budget",
    "vendor",
    "contract",
    "schedule",
    "update",
    "review",
    "team",
    "project",
    "pipeline",
    "incident",
    "metric",
    "dashboard",
    "backlog",
    "roadmap",
    "audit",
    "compliance",
    "escalation",
    "throughput",
    "latency",
    "capacity",
    "region",
    "cluster",
    "deployment",
    "rollback",
    "migration",
    "integration",
    "endpoint",
    "credential",
    "threshold",
]


@dataclass(frozen=True)
class SyntheticDocument:
    doc_name: str
    content: bytes
    fact_id: str


def _sample_word_count(rng: random.Random) -> int:
    # Log-normal-ish skew: most documents cluster in the low-to-mid range
    # with a long tail toward the 2000 word ceiling, rather than a flat
    # uniform spread between the bounds.
    raw = rng.lognormvariate(mu=6.6, sigma=0.5)
    return max(MIN_WORDS, min(MAX_WORDS, int(raw)))


def generate_synthetic_documents(n: int, seed: int = 42) -> list[SyntheticDocument]:
    rng = random.Random(seed)
    documents = []
    for index in range(n):
        fact_id = f"BENCH-{index:06d}-{rng.randrange(10**6):06d}"
        word_count = _sample_word_count(rng)
        # The template text below (title, fact-id sentences) adds ~32 words
        # of fixed overhead; subtract it so the assembled document lands
        # within [MIN_WORDS, MAX_WORDS] rather than drifting over MAX_WORDS.
        filler_word_count = max(word_count - 32, 1)
        filler = " ".join(rng.choice(_WORD_BANK) for _ in range(filler_word_count))
        text = (
            f"Synthetic Benchmark Document {index}\n\n"
            f"Unique fact identifier: {fact_id}. This document exists to validate "
            f"retrieval at scale for the GroundedRAG benchmark suite.\n\n"
            f"{filler}\n\n"
            f"Remember the fact identifier {fact_id} appears uniquely in this document only."
        )
        documents.append(
            SyntheticDocument(
                doc_name=f"bench-doc-{index:06d}.txt",
                content=text.encode("utf-8"),
                fact_id=fact_id,
            )
        )
    return documents
