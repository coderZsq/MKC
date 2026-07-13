from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from app.agent.checkpointer import AgentCheckpointer
from app.agent.graph import AgentGraph
from app.agent.router import route_after_validate, route_by_intent
from app.agent.state import AgentState
from app.core.exceptions import APIException, RetrievalForbiddenError
from app.models.agent import AgentRunRequest, AgentStreamEvent
from app.services.citation_service import CitationService, citation_to_event_data
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration for the Agent workflow."""

    enabled: bool = True
    recursion_limit: int = 12
    max_iterations: int = 3
    default_intent: str = "qa"
    enable_dynamic_intent: bool = False
    enable_web_search: bool = False
    compare_concurrency: int = 3
    fallback_message: str = "抱歉，暂无法生成答案，请稍后重试"
    emit_node_events: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> AgentConfig:
        raw = raw or {}
        sse = raw.get("sse") or {}
        return cls(
            enabled=bool(raw.get("enabled", True)),
            recursion_limit=int(raw.get("recursion_limit", 12)),
            max_iterations=int(raw.get("max_iterations", 3)),
            default_intent=str(raw.get("default_intent", "qa")),
            enable_dynamic_intent=bool(raw.get("enable_dynamic_intent", False)),
            enable_web_search=bool(raw.get("enable_web_search", False)),
            compare_concurrency=int(raw.get("compare_concurrency", 3)),
            fallback_message=str(raw.get("fallback_message", "抱歉，暂无法生成答案，请稍后重试")),
            emit_node_events=bool(sse.get("emit_node_events", True)),
        )


class AgentRunner:
    """Drives AgentGraph nodes and maps state changes to SSE events."""

    def __init__(
        self,
        graph: AgentGraph,
        config: AgentConfig,
        checkpointer: AgentCheckpointer | None = None,
        citation_service: CitationService | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self._graph = graph
        self._nodes = graph.nodes
        self._config = config
        self._checkpointer = checkpointer
        self._citation = citation_service
        self._memory = memory_service

    async def run_stream(self, request: AgentRunRequest) -> AsyncIterator[AgentStreamEvent]:
        state = self._initial_state(request)
        thread_id = request.conversation_id
        if self._checkpointer is not None:
            previous = self._checkpointer.load(thread_id)
            if previous:
                state["iterations"] = int(previous.get("iterations", 0))

        try:
            async for event in self._run_nodes(state, request):
                yield event
        except RetrievalForbiddenError as exc:
            yield self._error(request, "FORBIDDEN", exc.message)
        except RecursionError:
            yield self._error(request, "AGENT_TIMEOUT", "达到迭代上限")
        except APIException as exc:
            yield self._error(request, exc.code, exc.message)
        except Exception:
            logger.exception("agent workflow failed")
            yield self._error(request, "AGENT_INTERNAL_ERROR", "Agent 内部错误")

    async def _run_nodes(
        self, state: AgentState, request: AgentRunRequest
    ) -> AsyncIterator[AgentStreamEvent]:
        if self._memory is not None:
            state["memory_context"] = await self._memory.load_context(
                request.user_id, request.conversation_id, request.question
            )

        yield self._node_start("intent", request)
        await self._run_node("intent", state, self._nodes.intent_node)
        yield self._node_end("intent", request, {"intent": state.get("intent")})

        branch = route_by_intent(state)
        if branch in {"qa", "compare"}:
            yield self._node_start("retrieve", request)
            update = await self._nodes.retrieval_node(state)
            self._merge_state(state, update)
            yield self._node_end(
                "retrieve", request, {"chunks": len(state.get("retrieved_chunks", []))}
            )
            branch = "compare" if state.get("intent") == "compare" else "qa"

        if (
            branch == "summarize"
            and state.get("resource_ids")
            and not state.get("retrieved_chunks")
        ):
            yield self._node_start("retrieve", request)
            update = await self._nodes.retrieval_node(state)
            self._merge_state(state, update)
            yield self._node_end(
                "retrieve", request, {"chunks": len(state.get("retrieved_chunks", []))}
            )

        yield self._node_start(branch, request)
        answer_parts: list[str] = []
        reasoning_parts: list[str] = []
        chunk_index = 0
        reasoning_index = 0
        async for chunk in self._nodes.stream_generation(state, branch):
            if chunk.delta:
                answer_parts.append(chunk.delta)
                yield AgentStreamEvent(
                    event_type="chunk",
                    data={"message_id": request.message_id, "delta": chunk.delta, "index": chunk_index},
                )
                chunk_index += 1
            if chunk.reasoning_delta:
                reasoning_parts.append(chunk.reasoning_delta)
                yield AgentStreamEvent(
                    event_type="reasoning",
                    data={
                        "message_id": request.message_id,
                        "delta": chunk.reasoning_delta,
                        "index": reasoning_index,
                    },
                )
                reasoning_index += 1
            if chunk.finish_reason == "error":
                yield self._error(request, "AGENT_LLM_ERROR", "生成失败")
                return
        state["draft_answer"] = "".join(answer_parts) or self._config.fallback_message
        yield self._node_end(branch, request, {"draft_length": len(state["draft_answer"])})

        for _ in range(self._config.recursion_limit):
            yield self._node_start("validate", request)
            update = await self._nodes.validate_node(state)
            self._merge_state(state, update)
            yield self._node_end(
                "validate",
                request,
                {
                    "passed": state.get("validation_passed", True),
                    "iterations": state.get("iterations", 0),
                },
            )
            if route_after_validate(state) == "pass":
                break
            yield self._node_start("retrieve", request)
            update = await self._nodes.retrieval_node(state)
            self._merge_state(state, update)
            yield self._node_end(
                "retrieve", request, {"chunks": len(state.get("retrieved_chunks", []))}
            )
        else:
            raise RecursionError

        citations = self._build_citations(request, state)
        state["citations"] = citations
        for citation in citations:
            yield AgentStreamEvent(
                event_type="citation",
                data={"message_id": request.message_id, **citation},
            )

        if self._checkpointer is not None:
            self._checkpointer.save(request.conversation_id, dict(state))

        if self._memory is not None:
            await self._memory.save_turn(
                request.user_id,
                request.conversation_id,
                request.question,
                state.get("draft_answer", ""),
                reasoning="".join(reasoning_parts),
            )

        yield AgentStreamEvent(
            event_type="done",
            data={
                "message_id": request.message_id,
                "finish_reason": "stop",
                "iterations": state.get("iterations", 0),
                "low_confidence": state.get("low_confidence", False),
                "citation_count": len(citations),
            },
        )

    def _build_citations(self, request: AgentRunRequest, state: AgentState) -> list[dict[str, Any]]:
        chunks = state.get("retrieved_chunks", [])
        if self._citation is None or not chunks:
            return []
        result = self._citation.build_citations(
            answer=state.get("draft_answer", ""),
            chunks=list(chunks),
            authorized_resource_ids=set(request.resource_ids),
        )
        return [citation_to_event_data(citation) for citation in result.citations]

    async def _run_node(self, name: str, state: AgentState, fn: Any) -> None:
        update = await fn(state)
        self._merge_state(state, update)

    def _merge_state(self, state: AgentState, update: dict[str, Any]) -> None:
        for key, value in update.items():
            state[key] = value  # type: ignore[literal-required]

    def _initial_state(self, request: AgentRunRequest) -> AgentState:
        return {
            "messages": request.history,
            "intent": request.intent or "",
            "question": request.question,
            "conversation_id": request.conversation_id,
            "message_id": request.message_id,
            "user_id": request.user_id,
            "resource_ids": request.resource_ids,
            "retrieved_chunks": [],
            "draft_answer": "",
            "final_answer": "",
            "citations": [],
            "iterations": 0,
            "max_iterations": self._config.max_iterations,
            "validation_passed": True,
            "low_confidence": False,
            "error": None,
            "top_k": request.top_k,
            "score_threshold": request.score_threshold,
            "max_context_tokens": request.max_context_tokens,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "enable_web_search": request.enable_web_search,
        }

    def _node_start(self, node: str, request: AgentRunRequest) -> AgentStreamEvent:
        return AgentStreamEvent(
            event_type="node_start",
            data={
                "message_id": request.message_id,
                "node": node,
                "thread_id": request.conversation_id,
            },
        )

    def _node_end(
        self, node: str, request: AgentRunRequest, data: dict[str, Any]
    ) -> AgentStreamEvent:
        return AgentStreamEvent(
            event_type="node_end",
            data={"message_id": request.message_id, "node": node, **data},
        )

    def _error(self, request: AgentRunRequest, code: str, message: str) -> AgentStreamEvent:
        return AgentStreamEvent(
            event_type="error",
            data={
                "message_id": request.message_id,
                "conversation_id": request.conversation_id,
                "error_code": code,
                "message": message,
            },
        )
