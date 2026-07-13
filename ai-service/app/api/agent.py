import hmac
import logging
from collections.abc import AsyncIterator

from flask import Blueprint, Response, current_app, request
from pydantic import ValidationError as PydanticValidationError

from app.agent import AgentConfig, AgentGraph, AgentNodes, AgentRunner
from app.agent.checkpointer import AgentCheckpointer
from app.core.config import settings
from app.core.exceptions import APIException, LLMUnavailableError, ValidationException
from app.models.agent import AgentRunRequest
from app.services.llm.llm_client import sync_format_sse_stream

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__)


def _check_agent_internal_key() -> None:
    key = request.headers.get("X-Internal-Key")
    configured_key = settings.internal_api_key
    if not key or not configured_key or not hmac.compare_digest(key, configured_key):
        raise APIException("UNAUTHORIZED", "未授权访问", 401)


agent_bp.before_request(_check_agent_internal_key)


@agent_bp.post("/agent/run")
def run_agent() -> Response:
    """Run the Agent workflow and stream Server-Sent Events."""
    data = request.get_json(silent=True) or {}
    try:
        req = AgentRunRequest.model_validate(data)
    except PydanticValidationError as exc:
        logger.warning("Agent request validation failed: %s", exc)
        raise ValidationException("请求参数错误") from exc

    runner = _build_runner()

    async def _generate() -> AsyncIterator[str]:
        async for event in runner.run_stream(req):
            yield event.format_sse()

    try:
        return Response(
            sync_format_sse_stream(_generate()),
            status=200,
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except APIException:
        raise
    except Exception as exc:
        logger.exception("Agent stream failed")
        raise LLMUnavailableError() from exc


def _build_runner() -> AgentRunner:
    agent_cfg = AgentConfig.from_dict((current_app.config.get("AI_CONFIG") or {}).get("agent", {}))
    checkpointer = current_app.extensions.get("agent_checkpointer")
    if checkpointer is None:
        checkpointer = AgentCheckpointer()
        current_app.extensions["agent_checkpointer"] = checkpointer

    nodes = AgentNodes(
        current_app.extensions["retrieval"],
        current_app.extensions["llm"],
        config=agent_cfg,
    )
    graph = AgentGraph(nodes, checkpointer)
    return AgentRunner(graph, agent_cfg, checkpointer)
