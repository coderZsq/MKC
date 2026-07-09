from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import request

from app.core.config import settings
from app.core.exceptions import APIException

F = TypeVar("F", bound=Callable[..., Any])


def check_internal_key() -> None:
    key = request.headers.get("X-Internal-Key")
    if key is None:
        raise APIException("UNAUTHORIZED", "缺少内部调用密钥", 401)
    if key != settings.internal_api_key:
        raise APIException("FORBIDDEN", "非法内部调用", 403)


def require_internal_key(f: F) -> F:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        check_internal_key()
        return f(*args, **kwargs)

    return decorated  # type: ignore[return-value]
