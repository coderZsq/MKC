from __future__ import annotations

import asyncio
import logging

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.agent.tools import WebSearchTool
from app.api.dependencies import check_internal_key
from app.core.exceptions import InvalidRequestError
from app.core.response import make_response
from app.models.web_search import WebSearchRequest

logger = logging.getLogger(__name__)

web_search_bp = Blueprint("web_search", __name__)
web_search_bp.before_request(check_internal_key)


@web_search_bp.post("/tools/web-search")
def web_search() -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    try:
        req = WebSearchRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("Web search request validation failed: %s", exc)
        raise InvalidRequestError("查询参数非法") from exc

    search_tool: WebSearchTool = current_app.extensions["web_search_tool"]
    response = asyncio.run(search_tool.invoke(req.query, req.top_k))
    return make_response(data=response.model_dump(), status=200)
