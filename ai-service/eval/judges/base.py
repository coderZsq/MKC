from __future__ import annotations

from abc import ABC, abstractmethod

from eval.models import EvalCase
from eval.types import GeneratedAnswer, JudgeScores


class JudgeProvider(ABC):
    @abstractmethod
    async def score(self, case: EvalCase, answer: GeneratedAnswer) -> JudgeScores:
        raise NotImplementedError
