from app.agent.router import classify_by_rules, route_after_validate, route_by_intent


def test_classify_by_rules_supports_four_intents() -> None:
    assert classify_by_rules("请总结这个资源") == "summarize"
    assert classify_by_rules("对比资源 A 和 B") == "compare"
    assert classify_by_rules("写一段邀请文案") == "generate"
    assert classify_by_rules("这个概念是什么") == "qa"


def test_route_by_intent_dispatches_and_falls_back() -> None:
    assert route_by_intent({"intent": "summarize"}) == "summarize"
    assert route_by_intent({"intent": "compare"}) == "compare"
    assert route_by_intent({"intent": "unknown"}) == "qa"


def test_route_after_validate_retries_until_limit() -> None:
    assert route_after_validate({"validation_passed": True, "iterations": 1}) == "pass"
    assert (
        route_after_validate({"validation_passed": False, "iterations": 1, "max_iterations": 3})
        == "retry"
    )
    assert (
        route_after_validate({"validation_passed": False, "iterations": 3, "max_iterations": 3})
        == "pass"
    )
