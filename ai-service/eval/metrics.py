from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from eval.models import ExpectedCitation
from eval.types import AnswerCitation, EvalCaseResult, EvalSummary, JudgeScores

METRIC_NAMES = ("recall", "faithfulness", "relevance", "citation_accuracy")


def citation_overlap_score(
    expected_citations: Iterable[ExpectedCitation],
    actual_citations: Iterable[AnswerCitation],
) -> float:
    expected = {_citation_key(citation) for citation in expected_citations}
    actual = {_citation_key(citation) for citation in actual_citations}
    if not expected:
        return 1.0 if not actual else 0.0
    return len(expected.intersection(actual)) / len(expected)


def calculate_summary(results: list[EvalCaseResult]) -> EvalSummary:
    scored = [result for result in results if result.scores is not None]
    metric_values = {
        name: _average([getattr(result.scores, name) for result in scored if result.scores])
        for name in METRIC_NAMES
    }
    by_tag: dict[str, dict[str, float | int]] = {}
    grouped: dict[str, list[JudgeScores]] = defaultdict(list)
    for result in scored:
        if result.scores is None:
            continue
        for tag in result.tags:
            grouped[tag].append(result.scores)
    for tag, scores in grouped.items():
        by_tag[tag] = {
            "count": len(scores),
            **{name: _average([getattr(score, name) for score in scores]) for name in METRIC_NAMES},
        }
    failures = [result.case_id for result in results if result.status == "failed"]
    return EvalSummary(
        total_cases=len(results),
        passed_cases=len(results) - len(failures),
        failed_cases=len(failures),
        failures=failures,
        by_tag=by_tag,
        **metric_values,
    )


def _citation_key(citation: ExpectedCitation | AnswerCitation) -> tuple[object, ...]:
    return (
        citation.resource_id,
        citation.chunk_id,
        citation.page,
        citation.start_sec,
        citation.end_sec,
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
