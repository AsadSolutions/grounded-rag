"""GET /api/eval/results parses app/eval/RESULTS.md's '## Overall' table
into the JSON shape the frontend expects. Read-only: never touches
app/eval/ itself (Phase 3 is closed per CLAUDE.md 12a).
"""

import app.routers.eval as eval_router
import pytest
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient

SAMPLE_RESULTS_MD = """# Evaluation Results

Some prose about the run.

## Overall (2 passes, n=45 each)

| Metric             | Correction OFF (mean, min-max) | Correction ON (mean, min-max) | Delta (mean) |
| ------------------- | ------------------------------- | ------------------------------ | ------------- |
| Retrieval hit rate | 100.0% (100.0-100.0%)          | 98.6% (97.2-100.0%)           | -1.4pp       |
| Groundedness rate  | 96.7% (93.3-100.0%)            | 93.3% (91.1-95.6%)            | -3.3pp       |
| Not-found honesty  | 100.0% (100.0-100.0%)          | 100.0% (100.0-100.0%)         | +0.0pp       |

## Breakdown by category

### baseline (n=25)

| Metric             | Correction OFF (mean, min-max) | Correction ON (mean, min-max) | Delta (mean) |
| ------------------- | ------------------------------- | ------------------------------ | ------------- |
| Retrieval hit rate | 100.0% (100.0-100.0%)          | 100.0% (100.0-100.0%)         | +0.0pp       |

### Judge agreement (independent eval judge vs. the pipeline's internal groundedness check, correction ON only)

- Pass 1: 39/45 (86.7%)
- Pass 2: 37/45 (82.2%)
- Combined: 76/90 (84.4%)
"""


def test_parse_eval_results_extracts_overall_table_only():
    result = eval_router.parse_eval_results(SAMPLE_RESULTS_MD, generated_at="2026-07-10T00:00:00+00:00")

    assert result.sample is False
    assert result.generated_at == "2026-07-10T00:00:00+00:00"
    assert len(result.metrics) == 3
    assert result.metrics[0] == eval_router.EvalMetric(
        name="Retrieval hit rate", with_correction=0.986, without_correction=1.0, delta=-0.014
    )
    assert result.metrics[1] == eval_router.EvalMetric(
        name="Groundedness rate", with_correction=0.933, without_correction=0.967, delta=-0.033
    )
    assert result.metrics[2] == eval_router.EvalMetric(
        name="Not-found honesty", with_correction=1.0, without_correction=1.0, delta=0.0
    )
    assert result.judge_agreement == eval_router.JudgeAgreement(
        agreement_rate=0.844, agreed=76, total=90
    )


def test_parse_eval_results_raises_on_missing_overall_section():
    with pytest.raises(ValueError, match="Overall"):
        eval_router.parse_eval_results("# Evaluation Results\n\nNo table here.\n", generated_at="x")


def test_load_eval_results_404s_when_file_missing(tmp_path):
    missing = tmp_path / "RESULTS.md"

    with pytest.raises(HTTPException) as exc_info:
        eval_router.load_eval_results(missing)

    assert exc_info.value.status_code == 404


def test_load_eval_results_parses_existing_file(tmp_path):
    results_path = tmp_path / "RESULTS.md"
    results_path.write_text(SAMPLE_RESULTS_MD)

    result = eval_router.load_eval_results(results_path)

    assert result.sample is False
    assert len(result.metrics) == 3


def test_get_eval_results_endpoint_returns_parsed_json(monkeypatch, tmp_path):
    results_path = tmp_path / "RESULTS.md"
    results_path.write_text(SAMPLE_RESULTS_MD)
    monkeypatch.setattr(eval_router, "RESULTS_PATH", results_path)

    api = TestClient(app)
    resp = api.get("/api/eval/results")

    assert resp.status_code == 200
    body = resp.json()
    assert body["sample"] is False
    assert body["metrics"][0]["name"] == "Retrieval hit rate"


def test_get_eval_results_endpoint_404s_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(eval_router, "RESULTS_PATH", tmp_path / "missing.md")

    api = TestClient(app)
    resp = api.get("/api/eval/results")

    assert resp.status_code == 404
