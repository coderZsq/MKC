from __future__ import annotations

from app.agent.state import AgentState

VALID_INTENTS = {"summarize", "qa", "compare", "generate"}


def classify_by_rules(question: str, explicit_intent: str | None = None) -> str:
    """Classify a user question by deterministic rules for the first release."""
    if explicit_intent in VALID_INTENTS:
        return explicit_intent

    text = question.lower()
    if any(word in text for word in ("对比", "比较", "compare", "difference", "differences")):
        return "compare"
    if any(word in text for word in ("总结", "摘要", "概括", "summarize", "summary")):
        return "summarize"
    if any(word in text for word in ("生成", "写一段", "创作", "generate", "draft", "write")):
        return "generate"
    if question.strip():
        return "qa"
    return "qa"


def route_by_intent(state: AgentState) -> str:
    """Return the next workflow branch for the current intent."""
    intent = state.get("intent") or "qa"
    if intent not in VALID_INTENTS:
        return "qa"
    return intent


def route_after_validate(state: AgentState) -> str:
    """Route to END when validation passes or retry budget is exhausted."""
    if state.get("validation_passed", True):
        return "pass"
    iterations = state.get("iterations", 0)
    max_iterations = state.get("max_iterations", 3)
    if iterations >= max_iterations:
        return "pass"
    return "retry"
