from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval.answer_providers import StaticAnswerProvider
from eval.judges.llm_judge import LLMJudge
from eval.judges.mock_judge import MockJudge
from eval.models import EvalCase
from eval.pipeline import EvalPipeline, enforce_threshold, filter_cases, load_eval_cases
from eval.report import ReportWriter
from eval.types import EvalThreshold, GeneratedAnswer, JudgeScores

AI_SERVICE_ROOT = Path(__file__).resolve().parents[2]
SMOKE_DATASET = AI_SERVICE_ROOT / "eval" / "datasets" / "smoke_eval.jsonl"


def test_pipeline_reads_smoke_dataset_and_generates_answers(tmp_path: Path) -> None:
    # MKC-TC-S5-2-001, MKC-TC-S5-2-003, MKC-TC-S5-2-004:
    # smoke pipeline runs with mock judge/provider and writes JSON + Markdown.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.pipeline",
            "--dataset",
            str(SMOKE_DATASET),
            "--report-dir",
            str(tmp_path),
            "--judge",
            "mock",
            "--answer-provider",
            "mock",
            "--min-cases",
            "5",
            "--max-cases",
            "10",
        ],
        cwd=AI_SERVICE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "OK: evaluated 5 cases" in result.stdout
    json_reports = list(tmp_path.glob("eval_report_*.json"))
    markdown_reports = list(tmp_path.glob("eval_report_*.md"))
    assert len(json_reports) == 1
    assert len(markdown_reports) == 1
    payload = json.loads(json_reports[0].read_text(encoding="utf-8"))
    assert payload["summary"]["total_cases"] == 5
    assert all(case["answer"] for case in payload["cases"])


def test_filter_cases_by_tags_difficulty_and_resource_type() -> None:
    # MKC-TC-S5-2-005: filter supports tag, difficulty, and resource_type.
    cases = load_eval_cases(SMOKE_DATASET, min_cases=5, max_cases=10)

    citation_cases = filter_cases(cases, tags={"citation"})
    hard_pdf_cases = filter_cases(cases, difficulties={"hard"}, resource_types={"pdf"})

    assert citation_cases
    assert all("citation" in case.tags for case in citation_cases)
    assert [case.id for case in hard_pdf_cases] == ["rag-cross-smoke-003"]


def test_single_answer_failure_does_not_stop_batch() -> None:
    # MKC-TC-S5-2-008: one answer failure is recorded and the rest continue.
    cases = load_eval_cases(SMOKE_DATASET, min_cases=5, max_cases=10)[:2]
    provider = StaticAnswerProvider({cases[0].id: RuntimeError("answer provider failed")})
    pipeline = EvalPipeline(provider, MockJudge(), max_retries=0)

    report = asyncio.run(pipeline.run(cases))

    assert report.summary.total_cases == 2
    assert report.summary.failed_cases == 1
    assert report.cases[0].status == "failed"
    assert report.cases[0].error_code == "EVAL_ANSWER_FAILED"
    assert report.cases[1].status == "passed"


def test_judge_failure_is_retried_then_recorded() -> None:
    # MKC-TC-S5-2-009: judge timeout/failure retries and records failure.
    case = load_eval_cases(SMOKE_DATASET, min_cases=5, max_cases=10)[0]
    judge = MockJudge({case.id: TimeoutError("judge timeout")})
    pipeline = EvalPipeline(StaticAnswerProvider({}), judge, max_retries=2)

    report = asyncio.run(pipeline.run([case]))

    assert report.summary.failed_cases == 1
    assert report.cases[0].attempts == 3
    assert report.cases[0].error_code == "EVAL_JUDGE_TIMEOUT"
    assert judge.calls[case.id] == 3


def test_threshold_failure_returns_non_zero(tmp_path: Path) -> None:
    # MKC-TC-S5-2-010: high threshold makes CLI return non-zero.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.pipeline",
            "--dataset",
            str(SMOKE_DATASET),
            "--report-dir",
            str(tmp_path),
            "--judge",
            "mock",
            "--min-cases",
            "5",
            "--max-cases",
            "10",
            "--threshold-relevance",
            "0.99",
        ],
        cwd=AI_SERVICE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "EVAL_THRESHOLD_FAILED" in result.stderr


def test_enforce_threshold_detects_low_metrics() -> None:
    case = EvalCase.model_validate(
        {
            "id": "rag-temp-001",
            "question": "q",
            "expected_answer": "a",
            "resource_ids": ["res"],
            "expected_citations": [],
            "tags": ["no_answer"],
            "difficulty": "easy",
        }
    )
    scores = JudgeScores(
        recall=0.4,
        faithfulness=0.9,
        relevance=0.9,
        citation_accuracy=1.0,
        reason="test",
    )

    async def _run() -> int:
        report = await EvalPipeline(
            StaticAnswerProvider({case.id: GeneratedAnswer(answer="answer")}),
            MockJudge({case.id: scores}),
            max_retries=0,
        ).run([case])
        return enforce_threshold(report, EvalThreshold(recall=0.5))

    assert asyncio.run(_run()) == 1


def test_report_writer_rejects_sensitive_markers(tmp_path: Path) -> None:
    # MKC-TC-S5-2-006: reports must not contain API key/token/secret markers.
    case = EvalCase.model_validate(
        {
            "id": "rag-temp-001",
            "question": "q",
            "expected_answer": "a",
            "resource_ids": ["res"],
            "expected_citations": [],
            "tags": ["no_answer"],
            "difficulty": "easy",
        }
    )
    report = asyncio.run(
        EvalPipeline(
            StaticAnswerProvider({case.id: GeneratedAnswer(answer="api_key should not appear")}),
            MockJudge(),
            max_retries=0,
        ).run([case])
    )

    with pytest.raises(ValueError, match="sensitive marker"):
        ReportWriter(tmp_path).write(report)


def test_judge_prompt_excludes_environment_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    # MKC-TC-S5-2-007: prompt construction only includes case/answer payload, not env config.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-sensitive-value-1234567890")
    case = load_eval_cases(SMOKE_DATASET, min_cases=5, max_cases=10)[0]

    prompt = LLMJudge().build_prompt(case, GeneratedAnswer(answer="safe answer"))

    assert "sk-sensitive-value" not in prompt
    assert "OPENAI_API_KEY" not in prompt
    assert case.question in prompt
