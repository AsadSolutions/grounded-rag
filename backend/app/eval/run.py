import argparse
import json
from pathlib import Path

from app.eval.judge import judge_groundedness
from app.eval.schemas import GoldenQuestion, JudgeVerdict, QuestionOutcome, RunSummary
from app.graph.build import build_graph
from app.models import GraphState, ScoredChunk

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
RESULTS_PATH = Path(__file__).parent / "RESULTS.md"
TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts"

NOT_FOUND_PHRASE = "not found in the documents"


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> list[GoldenQuestion]:
    data = json.loads(path.read_text())
    return [GoldenQuestion(**item) for item in data]


def matches_expected_chunk(retrieved_chunks: list[ScoredChunk], question: GoldenQuestion) -> bool:
    for expected in question.expected_chunks:
        for chunk in retrieved_chunks:
            if chunk.doc_name == expected.doc_name and expected.contains.lower() in chunk.text.lower():
                return True
    return False


def said_not_found(answer: str) -> bool:
    return NOT_FOUND_PHRASE in answer.lower()


def _execute(question: GoldenQuestion, graph, judge_fn=judge_groundedness) -> tuple[GraphState, JudgeVerdict]:
    state = GraphState(question=question.question, tenant_id=question.tenant_id)
    result = GraphState(**graph.invoke(state))
    verdict = judge_fn(question.question, result.answer, result.retrieved_chunks)
    return result, verdict


def _outcome_from(question: GoldenQuestion, result: GraphState, verdict: JudgeVerdict) -> QuestionOutcome:
    return QuestionOutcome(
        question_id=question.id,
        tenant_id=question.tenant_id,
        category=question.category,
        retrieval_hit=None if question.unanswerable else matches_expected_chunk(result.retrieved_chunks, question),
        grounded=verdict.grounded,
        internal_groundedness=result.groundedness,
        honest_refusal=said_not_found(result.answer) if question.unanswerable else None,
        answer=result.answer,
        rewrite_count=result.rewrite_count,
        low_confidence=result.low_confidence,
    )


def judge_agreement_count(outcomes: list[QuestionOutcome]) -> tuple[int, int]:
    """(agreements, comparable) — comparable counts outcomes where the pipeline's internal
    groundedness_check actually ran (always true for correction ON, never for correction OFF,
    since OFF bypasses that node entirely). agreements counts how many of those had the
    internal verdict match the independent eval judge's verdict."""
    comparable = [o for o in outcomes if o.internal_groundedness is not None]
    agreements = sum(1 for o in comparable if o.internal_groundedness == o.grounded)
    return agreements, len(comparable)


def run_question(question: GoldenQuestion, graph, judge_fn=judge_groundedness) -> QuestionOutcome:
    result, verdict = _execute(question, graph, judge_fn=judge_fn)
    return _outcome_from(question, result, verdict)


def _chunk_transcript(chunk: ScoredChunk) -> dict:
    return {"chunk_id": chunk.chunk_id, "doc_name": chunk.doc_name, "score": chunk.score, "text": chunk.text}


def _grade_transcript(grade) -> dict:
    return {"chunk_id": grade.chunk_id, "relevant": grade.relevant, "reason": grade.reason}


def _trace_transcript(trace) -> list[dict]:
    return [{"node": entry.node, "message": entry.message} for entry in trace]


def _config_transcript(result: GraphState, verdict: JudgeVerdict) -> dict:
    return {
        "answer": result.answer,
        "retrieved_chunks_passed_to_judge": [_chunk_transcript(c) for c in result.retrieved_chunks],
        "grades": [_grade_transcript(g) for g in result.grades],
        "rewrite_count": result.rewrite_count,
        "trace": _trace_transcript(result.trace),
        "judge_verdict": verdict.model_dump(),
        "pipeline_internal_groundedness": result.groundedness,
        "pipeline_internal_groundedness_failure_reason": result.groundedness_failure_reason,
    }


def build_question_transcript(
    question: GoldenQuestion,
    result_on: GraphState,
    verdict_on: JudgeVerdict,
    result_off: GraphState,
    verdict_off: JudgeVerdict,
) -> dict:
    return {
        "question_id": question.id,
        "question": question.question,
        "tenant_id": question.tenant_id,
        "category": question.category,
        "unanswerable": question.unanswerable,
        "correction_on": _config_transcript(result_on, verdict_on),
        "correction_off": _config_transcript(result_off, verdict_off),
    }


def write_transcript(transcript: dict, directory: Path = TRANSCRIPTS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{transcript['question_id']}.json"
    path.write_text(json.dumps(transcript, indent=2))
    return path


def summarize(config: str, outcomes: list[QuestionOutcome]) -> RunSummary:
    answerable = [o for o in outcomes if o.retrieval_hit is not None]
    unanswerable = [o for o in outcomes if o.honest_refusal is not None]

    hit_rate = sum(o.retrieval_hit for o in answerable) / len(answerable) if answerable else None
    groundedness_rate = sum(o.grounded for o in outcomes) / len(outcomes) if outcomes else 0.0
    honesty_rate = sum(o.honest_refusal for o in unanswerable) / len(unanswerable) if unanswerable else None

    return RunSummary(
        config=config,
        n_questions=len(outcomes),
        retrieval_hit_rate=hit_rate,
        groundedness_rate=groundedness_rate,
        not_found_honesty=honesty_rate,
    )


CATEGORY_ORDER = ["baseline", "rewrite_bait", "multi_chunk", "distractor_trap", "near_miss_unanswerable"]


def summarize_by_category(config: str, outcomes: list[QuestionOutcome]) -> dict[str, RunSummary]:
    categories = sorted({o.category for o in outcomes}, key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else len(CATEGORY_ORDER))
    return {
        category: summarize(f"{config}:{category}", [o for o in outcomes if o.category == category])
        for category in categories
    }


def run_eval(
    questions: list[GoldenQuestion] | None = None,
    graph_on=None,
    graph_off=None,
    judge_fn=judge_groundedness,
    verbose: bool = False,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> tuple[RunSummary, RunSummary, list[QuestionOutcome], list[QuestionOutcome]]:
    questions = questions if questions is not None else load_golden_set()
    graph_on = graph_on or build_graph(correction_enabled=True)
    graph_off = graph_off or build_graph(correction_enabled=False)

    outcomes_on = []
    outcomes_off = []
    for question in questions:
        result_on, verdict_on = _execute(question, graph_on, judge_fn=judge_fn)
        result_off, verdict_off = _execute(question, graph_off, judge_fn=judge_fn)

        outcomes_on.append(_outcome_from(question, result_on, verdict_on))
        outcomes_off.append(_outcome_from(question, result_off, verdict_off))

        if verbose:
            transcript = build_question_transcript(question, result_on, verdict_on, result_off, verdict_off)
            write_transcript(transcript, directory=transcripts_dir)

    summary_on = summarize("correction_on", outcomes_on)
    summary_off = summarize("correction_off", outcomes_off)

    return summary_on, summary_off, outcomes_on, outcomes_off


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _delta(on: float | None, off: float | None) -> str:
    if on is None or off is None:
        return "n/a"
    delta = (on - off) * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}pp"


def _metric_rows(summary_on: RunSummary, summary_off: RunSummary) -> list[str]:
    return [
        f"| Retrieval hit rate | {_pct(summary_off.retrieval_hit_rate)} | {_pct(summary_on.retrieval_hit_rate)} | "
        f"{_delta(summary_on.retrieval_hit_rate, summary_off.retrieval_hit_rate)} |",
        f"| Groundedness rate | {_pct(summary_off.groundedness_rate)} | {_pct(summary_on.groundedness_rate)} | "
        f"{_delta(summary_on.groundedness_rate, summary_off.groundedness_rate)} |",
        f"| Not-found honesty | {_pct(summary_off.not_found_honesty)} | {_pct(summary_on.not_found_honesty)} | "
        f"{_delta(summary_on.not_found_honesty, summary_off.not_found_honesty)} |",
    ]


def render_results_md(summary_on: RunSummary, summary_off: RunSummary) -> str:
    lines = [
        "# Evaluation Results",
        "",
        f"Raw output of `python -m app.eval.run` against the real OpenAI API and the seeded "
        f"demo tenants ({summary_on.n_questions} golden questions across several categories "
        "— see `app/eval/golden_set.json` for the exact set and category tags). Never "
        "hand-edited: regenerate with the command above if the golden set, prompts, or "
        "models change.",
        "",
        "## Results table",
        "",
        "| Metric | Correction OFF | Correction ON | Delta |",
        "| --- | --- | --- | --- |",
        *_metric_rows(summary_on, summary_off),
        "",
    ]
    return "\n".join(lines)


def render_category_breakdown_md(
    breakdown_on: dict[str, RunSummary],
    breakdown_off: dict[str, RunSummary],
) -> str:
    lines = ["## Breakdown by category", ""]
    for category in breakdown_on:
        summary_on = breakdown_on[category]
        summary_off = breakdown_off[category]
        lines.append(f"### {category} (n={summary_on.n_questions})")
        lines.append("")
        lines.append("| Metric | Correction OFF | Correction ON | Delta |")
        lines.append("| --- | --- | --- | --- |")
        lines.extend(_metric_rows(summary_on, summary_off))
        lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the GroundedRAG eval harness.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Write a full per-question transcript (chunks, answer, judge verdict, pipeline verdict) to eval/transcripts/",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only run the first N golden-set questions (for quick diagnostics). Disables writing RESULTS.md.",
    )
    parser.add_argument(
        "--answerable-only",
        action="store_true",
        help="Skip the deliberately unanswerable questions. Disables writing RESULTS.md.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    is_full_run = args.limit is None and not args.answerable_only

    questions = load_golden_set()
    if args.answerable_only:
        questions = [q for q in questions if not q.unanswerable]
    if args.limit is not None:
        questions = questions[: args.limit]

    summary_on, summary_off, outcomes_on, outcomes_off = run_eval(questions=questions, verbose=args.verbose)
    breakdown_on = summarize_by_category("correction_on", outcomes_on)
    breakdown_off = summarize_by_category("correction_off", outcomes_off)

    markdown = render_results_md(summary_on, summary_off) + "\n" + render_category_breakdown_md(breakdown_on, breakdown_off)

    if is_full_run:
        RESULTS_PATH.write_text(markdown)
    else:
        print(f"Partial run ({len(questions)} question(s)) — RESULTS.md was NOT overwritten.")
    print(markdown)

    agreements, comparable = judge_agreement_count(outcomes_on)
    if comparable:
        print(f"Judge agreement (correction ON): {agreements}/{comparable} ({agreements / comparable * 100:.1f}%)")


if __name__ == "__main__":
    main()
