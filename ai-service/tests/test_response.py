from app.core.response import make_response


def test_make_response_default() -> None:
    response, status = make_response(data={"foo": "bar"})
    assert status == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"] == {"foo": "bar"}
    assert data["error"] is None
    assert "timestamp" in data["meta"]


def test_make_response_error() -> None:
    response, status = make_response(
        success=False,
        error={"code": "ERR", "message": "bad"},
        status=400,
    )
    assert status == 400

    data = response.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "ERR"
    assert data["error"]["message"] == "bad"
    assert data["error"]["retryable"] is False
    assert data["error"]["trace_id"] == ""


def test_make_response_retryable_error_sanitizes_message() -> None:
    response, status = make_response(
        success=False,
        error={"code": "LLM_TIMEOUT", "message": "select * from secrets"},
        status=504,
    )
    assert status == 504

    data = response.get_json()
    assert data["error"]["message"] == "系统异常，请稍后重试"
    assert data["error"]["retryable"] is True
