from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import request

from app.core.config import settings
from app.core.exceptions import APIException

F = TypeVar("F", bound=Callable[..., Any])


def check_internal_key() -> None:
    key = request.headers.get("X-Internal-Key")
    if key != settings.internal_api_key:
        raise APIException("UNAUTHORIZED", "非法内部调用", 401)


def require_internal_key(f: F) -> F:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        check_internal_key()
        return f(*args, **kwargs)

    return decorated  # type: ignore[return-value]
