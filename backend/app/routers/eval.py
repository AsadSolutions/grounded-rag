"""GET /api/eval/results — a read-only view over the harness's published
app/eval/RESULTS.md. This module only reads that file; nothing under
app/eval/ is modified (Phase 3 is closed per CLAUDE.md 12a).
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from app.eval.run import RESULTS_PATH
from app.models import EvalMetric, EvalResultsResponse, JudgeAgreement
from fastapi import APIRouter, HTTPException

router = APIRouter()

_PERCENT_RE = re.compile(r"^(-?\d+(?:\.\d+)?)%")
_DELTA_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)pp")
_COMBINED_RE = re.compile(r"^-\s*Combined:\s*(\d+)/(\d+)\s*\((\d+(?:\.\d+)?)%\)")


def _parse_percent_cell(cell: str) -> float:
    match = _PERCENT_RE.match(cell.strip())
    if not match:
        raise ValueError(f"Could not parse a percentage from eval results cell: {cell!r}")
    # round() clears binary floating-point noise from the /100 division
    # (e.g. 96.7 / 100 == 0.9670000000000001, not 0.967) without losing
    # any real precision — source values have at most one decimal place.
    return round(float(match.group(1)) / 100, 6)


def _parse_delta_cell(cell: str) -> float:
    match = _DELTA_RE.match(cell.strip())
    if not match:
        raise ValueError(f"Could not parse a delta from eval results cell: {cell!r}")
    return round(float(match.group(1)) / 100, 6)


def _extract_overall_table_rows(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().startswith("## Overall")), None)
    if start is None:
        raise ValueError("RESULTS.md has no '## Overall' section")

    table_lines = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break
    if len(table_lines) < 3:
        raise ValueError("RESULTS.md '## Overall' table has no data rows")
    return table_lines[2:]  


def _extract_judge_agreement(markdown: str) -> JudgeAgreement:
    lines = markdown.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().startswith("### Judge agreement")), None)
    if start is None:
        raise ValueError("RESULTS.md has no '### Judge agreement' section")

    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("##"):
            break
        match = _COMBINED_RE.match(stripped)
        if match:
            agreed, total, rate = match.groups()
            return JudgeAgreement(
                agreement_rate=round(float(rate) / 100, 6),
                agreed=int(agreed),
                total=int(total),
            )
    raise ValueError("RESULTS.md 'Judge agreement' section has no 'Combined:' line")


def parse_eval_results(markdown: str, generated_at: str) -> EvalResultsResponse:
    metrics = []
    for row in _extract_overall_table_rows(markdown):
        name, off_cell, on_cell, delta_cell = (cell.strip() for cell in row.strip("|").split("|"))
        metrics.append(
            EvalMetric(
                name=name,
                with_correction=_parse_percent_cell(on_cell),
                without_correction=_parse_percent_cell(off_cell),
                delta=_parse_delta_cell(delta_cell),
            )
        )
    return EvalResultsResponse(
        generated_at=generated_at,
        sample=False,
        metrics=metrics,
        judge_agreement=_extract_judge_agreement(markdown),
    )


def load_eval_results(path: Path) -> EvalResultsResponse:
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="No eval results yet — run `python -m app.eval.run` to generate app/eval/RESULTS.md.",
        )
    generated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    try:
        return parse_eval_results(path.read_text(), generated_at)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Could not parse eval results: {exc}") from exc


@router.get("/api/eval/results", response_model=EvalResultsResponse)
def get_eval_results() -> EvalResultsResponse:
    return load_eval_results(RESULTS_PATH)
