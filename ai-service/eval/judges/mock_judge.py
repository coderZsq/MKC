from __future__ import annotations

from collections.abc import Mapping

from eval.judges.base import JudgeProvider
from eval.metrics import citation_overlap_score
from eval.models import EvalCase
from eval.types import GeneratedAnswer, JudgeScores


class MockJudge(JudgeProvider):
    def __init__(self, overrides: Mapping[str, JudgeScores | Exception] | None = None) -> None:
        self._overrides = dict(overrides or {})
        self.calls: dict[str, int] = {}

    async def score(self, case: EvalCase, answer: GeneratedAnswer) -> JudgeScores:
        self.calls[case.id] = self.calls.get(case.id, 0) + 1
        override = self._overrides.get(case.id)
        if isinstance(override, Exception):
            raise override
        if override is not None:
            return override

        citation_accuracy = citation_overlap_score(case.expected_citations, answer.citations)
        no_answer = "no_answer" in case.tags
        answer_text = answer.answer.lower()
        expected_tokens = {
            token
            for token in case.expected_answer.lower().replace("，", " ").replace("。", " ").split()
            if len(token) >= 2
        }
        matched_tokens = {token for token in expected_tokens if token in answer_text}
        recall = (
            1.0 if no_answer else _ratio(len(matched_tokens), len(expected_tokens), default=0.85)
        )
        relevance = 0.95 if case.question[:4].lower() not in answer_text else 0.85
        faithfulness = (
            1.0 if (no_answer or answer.citations or not case.expected_citations) else 0.55
        )
        return JudgeScores(
            recall=round(recall, 4),
            faithfulness=round(faithfulness, 4),
            relevance=round(relevance, 4),
            citation_accuracy=round(citation_accuracy, 4),
            reason="mock judge compared expected answer hints and citation overlap",
            evidence=[case.id, *case.resource_ids],
        )


def _ratio(numerator: int, denominator: int, *, default: float) -> float:
    if denominator == 0:
        return default
    return numerator / denominator
