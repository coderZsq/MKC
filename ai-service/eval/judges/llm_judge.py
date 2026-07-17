from __future__ import annotations

import json
from pathlib import Path

from eval.judges.base import JudgeProvider
from eval.models import EvalCase
from eval.types import GeneratedAnswer, JudgeScores

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "judge_v1.md"


class LLMJudge(JudgeProvider):
    """Versioned judge prompt builder.

    The network call is intentionally not implemented in S5-2 so CI and local
    runs stay deterministic. Real provider wiring can parse the prompt returned
    by :meth:`build_prompt` and validate the model JSON with ``JudgeScores``.
    """

    def __init__(self, model: str = "judge-v1") -> None:
        self._model = model
        self._template = PROMPT_PATH.read_text(encoding="utf-8")

    def build_prompt(self, case: EvalCase, answer: GeneratedAnswer) -> str:
        safe_payload = {
            "case_id": case.id,
            "question": case.question,
            "expected_answer": case.expected_answer,
            "resource_ids": case.resource_ids,
            "expected_citations": [citation.model_dump() for citation in case.expected_citations],
            "answer": answer.answer,
            "answer_citations": [citation.model_dump() for citation in answer.citations],
            "tags": case.tags,
            "difficulty": case.difficulty,
            "judge_model": self._model,
        }
        return self._template.replace(
            "{{ payload_json }}", json.dumps(safe_payload, ensure_ascii=False, indent=2)
        )

    async def score(self, case: EvalCase, answer: GeneratedAnswer) -> JudgeScores:
        raise RuntimeError("LLMJudge remote scoring is not configured; use --judge mock in CI")
