from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Mapping

from eval.models import EvalCase
from eval.types import AnswerCitation, GeneratedAnswer


class AnswerProvider(ABC):
    @abstractmethod
    async def answer(self, case: EvalCase) -> GeneratedAnswer:
        raise NotImplementedError


class MockAnswerProvider(AnswerProvider):
    async def answer(self, case: EvalCase) -> GeneratedAnswer:
        citations = [
            AnswerCitation(
                resource_id=citation.resource_id,
                chunk_id=citation.chunk_id,
                page=citation.page,
                start_sec=citation.start_sec,
                end_sec=citation.end_sec,
            )
            for citation in case.expected_citations
        ]
        if "no_answer" in case.tags:
            answer = f"根据当前知识库，未找到可支持该问题的资料。期望处理：{case.expected_answer}"
        else:
            answer = f"{case.expected_answer}（基于评估样本 {case.id} 的 mock RAG 回答）"
        return GeneratedAnswer(answer=answer, citations=citations)


class StaticAnswerProvider(AnswerProvider):
    def __init__(self, answers: Mapping[str, GeneratedAnswer | Exception]) -> None:
        self._answers = dict(answers)

    async def answer(self, case: EvalCase) -> GeneratedAnswer:
        value = self._answers.get(case.id)
        if isinstance(value, Exception):
            raise value
        if value is None:
            return await MockAnswerProvider().answer(case)
        return value


class HTTPAnswerProvider(AnswerProvider):
    def __init__(self, endpoint: str, internal_api_key: str, timeout_seconds: float = 60.0) -> None:
        self._endpoint = endpoint
        self._internal_api_key = internal_api_key
        self._timeout_seconds = timeout_seconds

    async def answer(self, case: EvalCase) -> GeneratedAnswer:
        payload = {
            "question": case.question,
            "resource_ids": case.resource_ids,
            "conversation_id": f"eval-{case.id}",
            "message_id": f"eval-msg-{case.id}",
            "user_id": "eval-runner",
        }
        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Internal-API-Key": self._internal_api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"RAG answer request failed: {exc}") from exc

        data = json.loads(body)
        citations = [
            AnswerCitation.model_validate(item)
            for item in data.get("citations", [])
            if isinstance(item, dict)
        ]
        answer = data.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("RAG answer response missing answer")
        return GeneratedAnswer(answer=answer, citations=citations, raw=data)
