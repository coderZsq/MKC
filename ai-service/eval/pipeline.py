from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from eval.answer_providers import AnswerProvider, HTTPAnswerProvider, MockAnswerProvider
from eval.judges import JudgeProvider, LLMJudge, MockJudge
from eval.metrics import calculate_summary
from eval.models import EvalCase
from eval.report import ReportWriter
from eval.types import EvalCaseResult, EvalReport, EvalThreshold, GeneratedAnswer, JudgeScores
from eval.validate_dataset import DatasetValidationError, load_jsonl, validate_cases


class EvalPipeline:
    def __init__(
        self,
        answer_provider: AnswerProvider,
        judge: JudgeProvider,
        *,
        max_retries: int = 2,
    ) -> None:
        self._answer_provider = answer_provider
        self._judge = judge
        self._max_retries = max_retries

    async def run(self, cases: Sequence[EvalCase]) -> EvalReport:
        results: list[EvalCaseResult] = []
        for case in cases:
            results.append(await self._run_case(case))
        return EvalReport(summary=calculate_summary(results), cases=results)

    async def _run_case(self, case: EvalCase) -> EvalCaseResult:
        attempts = 0
        last_error: Exception | None = None
        while attempts <= self._max_retries:
            attempts += 1
            try:
                answer = await self._answer_provider.answer(case)
                scores = await self._judge.score(case, answer)
                return _passed_result(case, answer, scores=scores, attempts=attempts)
            except Exception as exc:  # noqa: BLE001 - per-case isolation is the feature here.
                last_error = exc
        error_message = str(last_error) if last_error else "unknown eval failure"
        return EvalCaseResult(
            case_id=case.id,
            question=case.question,
            tags=case.tags,
            difficulty=case.difficulty,
            resource_ids=case.resource_ids,
            status="failed",
            error_code=_error_code(last_error),
            error_message=error_message,
            attempts=attempts,
        )


def filter_cases(
    cases: Sequence[EvalCase],
    *,
    tags: set[str] | None = None,
    difficulties: set[str] | None = None,
    resource_types: set[str] | None = None,
) -> list[EvalCase]:
    filtered: list[EvalCase] = []
    for case in cases:
        if tags and tags.isdisjoint(case.tags):
            continue
        if difficulties and case.difficulty not in difficulties:
            continue
        if resource_types and resource_types.isdisjoint(_resource_types(case)):
            continue
        filtered.append(case)
    return filtered


def load_eval_cases(dataset: Path, *, min_cases: int, max_cases: int) -> list[EvalCase]:
    loaded = load_jsonl(dataset)
    return validate_cases(
        loaded,
        min_cases=min_cases,
        max_cases=max_cases,
        required_tags=set(),
    )


def enforce_threshold(report: EvalReport, threshold: EvalThreshold) -> int:
    below = report.summary.metric_below_thresholds(threshold)
    return 1 if below else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MKC LLM-as-judge evaluation.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--judge", choices=["mock", "llm"], default="mock")
    parser.add_argument("--answer-provider", choices=["mock", "http"], default="mock")
    parser.add_argument("--answer-endpoint", default="http://localhost:5000/ai/v1/chat")
    parser.add_argument("--tags", default="", help="Comma-separated tags; OR semantics.")
    parser.add_argument("--difficulty", default="", help="Comma-separated difficulty values.")
    parser.add_argument("--resource-type", default="", help="Comma-separated resource types.")
    parser.add_argument("--min-cases", type=int, default=1)
    parser.add_argument("--max-cases", type=int, default=1000)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--threshold-recall", type=float, default=0.75)
    parser.add_argument("--threshold-faithfulness", type=float, default=0.8)
    parser.add_argument("--threshold-relevance", type=float, default=0.8)
    parser.add_argument("--threshold-citation-accuracy", type=float, default=0.7)
    return parser


async def run_from_args(args: argparse.Namespace) -> tuple[EvalReport, tuple[Path, Path], int]:
    cases = load_eval_cases(args.dataset, min_cases=args.min_cases, max_cases=args.max_cases)
    cases = filter_cases(
        cases,
        tags=_csv(args.tags),
        difficulties=_csv(args.difficulty),
        resource_types=_csv(args.resource_type),
    )
    if not cases:
        raise DatasetValidationError("EVAL_DATASET_NOT_FOUND", "no eval cases matched filters")

    pipeline = EvalPipeline(
        answer_provider=_build_answer_provider(args),
        judge=_build_judge(args),
        max_retries=args.max_retries,
    )
    report = await pipeline.run(cases)
    report_paths = ReportWriter(args.report_dir).write(report)
    threshold = EvalThreshold(
        recall=args.threshold_recall,
        faithfulness=args.threshold_faithfulness,
        relevance=args.threshold_relevance,
        citation_accuracy=args.threshold_citation_accuracy,
    )
    return report, report_paths, enforce_threshold(report, threshold)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report, report_paths, threshold_status = asyncio.run(run_from_args(args))
    except DatasetValidationError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI should return a readable failure.
        print(f"EVAL_PIPELINE_FAILED: {exc}", file=sys.stderr)
        return 1

    print(
        f"OK: evaluated {report.summary.total_cases} cases; reports: {report_paths[0]}, {report_paths[1]}"
    )
    if threshold_status:
        print(
            "EVAL_THRESHOLD_FAILED: evaluation metrics below configured threshold", file=sys.stderr
        )
    return threshold_status


def _passed_result(
    case: EvalCase,
    answer: GeneratedAnswer,
    *,
    scores: JudgeScores,
    attempts: int,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_id=case.id,
        question=case.question,
        tags=case.tags,
        difficulty=case.difficulty,
        resource_ids=case.resource_ids,
        answer=answer.answer,
        citations=answer.citations,
        scores=scores,
        attempts=attempts,
    )


def _build_answer_provider(args: argparse.Namespace) -> AnswerProvider:
    if args.answer_provider == "mock":
        return MockAnswerProvider()
    internal_key = os.environ.get("INTERNAL_API_KEY", "")
    if not internal_key:
        raise RuntimeError("INTERNAL_API_KEY is required for --answer-provider http")
    return HTTPAnswerProvider(args.answer_endpoint, internal_key)


def _build_judge(args: argparse.Namespace) -> JudgeProvider:
    if args.judge == "mock":
        return MockJudge()
    return LLMJudge()


def _csv(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _resource_types(case: EvalCase) -> set[str]:
    types = set(case.tags).intersection({"audio", "pdf"})
    for resource_id in case.resource_ids:
        if "audio" in resource_id:
            types.add("audio")
        if "pdf" in resource_id:
            types.add("pdf")
    return types


def _error_code(exc: Exception | None) -> str:
    if exc is None:
        return "EVAL_CASE_FAILED"
    message = str(exc).lower()
    if "timeout" in message:
        return "EVAL_JUDGE_TIMEOUT"
    if "answer" in message or "rag" in message:
        return "EVAL_ANSWER_FAILED"
    return "EVAL_CASE_FAILED"


if __name__ == "__main__":
    raise SystemExit(main())
