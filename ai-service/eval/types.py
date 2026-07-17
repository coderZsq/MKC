from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MetricName = Literal["recall", "faithfulness", "relevance", "citation_accuracy"]


class AnswerCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: str = Field(min_length=1)
    chunk_id: str | None = Field(default=None, min_length=1)
    page: int | None = Field(default=None, ge=1)
    start_sec: float | None = Field(default=None, ge=0)
    end_sec: float | None = Field(default=None, ge=0)


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    citations: list[AnswerCitation] = Field(default_factory=list)
    raw: dict[str, object] = Field(default_factory=dict)


class JudgeScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recall: float = Field(ge=0, le=1)
    faithfulness: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    citation_accuracy: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)


class EvalThreshold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recall: float = Field(default=0.75, ge=0, le=1)
    faithfulness: float = Field(default=0.8, ge=0, le=1)
    relevance: float = Field(default=0.8, ge=0, le=1)
    citation_accuracy: float = Field(default=0.7, ge=0, le=1)


class EvalCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    question: str
    tags: list[str]
    difficulty: str
    resource_ids: list[str]
    answer: str | None = None
    citations: list[AnswerCitation] = Field(default_factory=list)
    scores: JudgeScores | None = None
    status: Literal["passed", "failed"] = "passed"
    error_code: str | None = None
    error_message: str | None = None
    attempts: int = Field(default=1, ge=1)


class EvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cases: int
    passed_cases: int
    failed_cases: int
    recall: float
    faithfulness: float
    relevance: float
    citation_accuracy: float
    by_tag: dict[str, dict[str, float | int]] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)

    def metric_below_thresholds(self, threshold: EvalThreshold) -> dict[str, tuple[float, float]]:
        metrics = {
            "recall": self.recall,
            "faithfulness": self.faithfulness,
            "relevance": self.relevance,
            "citation_accuracy": self.citation_accuracy,
        }
        thresholds = threshold.model_dump()
        return {
            name: (value, thresholds[name])
            for name, value in metrics.items()
            if value < thresholds[name]
        }


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: EvalSummary
    cases: list[EvalCaseResult]
