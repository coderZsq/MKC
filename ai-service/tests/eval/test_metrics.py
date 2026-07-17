from __future__ import annotations

from eval.metrics import calculate_summary, citation_overlap_score
from eval.models import ExpectedCitation
from eval.types import AnswerCitation, EvalCaseResult, JudgeScores


def test_citation_overlap_score_matches_expected_citations() -> None:
    expected = [
        ExpectedCitation(resource_id="res_pdf_demo", chunk_id="chunk-1", page=1),
        ExpectedCitation(resource_id="res_audio_demo", chunk_id="chunk-2", start_sec=1, end_sec=3),
    ]
    actual = [
        AnswerCitation(resource_id="res_pdf_demo", chunk_id="chunk-1", page=1),
        AnswerCitation(resource_id="res_pdf_demo", chunk_id="wrong", page=2),
    ]

    assert citation_overlap_score(expected, actual) == 0.5


def test_calculate_summary_outputs_four_core_metrics() -> None:
    # MKC-TC-S5-2-002: metric aggregation returns recall, faithfulness, relevance,
    # and citation accuracy, including tag-level micro averages.
    results = [
        _result("case-1", ["citation"], 1.0, 0.8, 0.9, 0.7),
        _result("case-2", ["citation", "audio"], 0.5, 1.0, 0.7, 0.9),
    ]

    summary = calculate_summary(results)

    assert summary.total_cases == 2
    assert summary.passed_cases == 2
    assert summary.failed_cases == 0
    assert summary.recall == 0.75
    assert summary.faithfulness == 0.9
    assert summary.relevance == 0.8
    assert summary.citation_accuracy == 0.8
    assert summary.by_tag["citation"]["count"] == 2
    assert summary.by_tag["audio"]["recall"] == 0.5


def _result(
    case_id: str,
    tags: list[str],
    recall: float,
    faithfulness: float,
    relevance: float,
    citation_accuracy: float,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_id=case_id,
        question="question",
        tags=tags,
        difficulty="easy",
        resource_ids=["res"],
        answer="answer",
        scores=JudgeScores(
            recall=recall,
            faithfulness=faithfulness,
            relevance=relevance,
            citation_accuracy=citation_accuracy,
            reason="test",
        ),
    )
