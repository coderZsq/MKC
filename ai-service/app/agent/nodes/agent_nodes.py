from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.agent.router import classify_by_rules
from app.agent.state import AgentState
from app.agent.tools import RetrievalTool, SummarizerTool, WebSearchTool
from app.core.exceptions import APIException, RetrievalForbiddenError
from app.models.retrieval import RetrievalChunk
from app.services.llm.llm_client import LLMClient
from app.services.llm.models import LLMRequest, Message
from app.services.retrieval.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class AgentNodes:
    """Pure-ish Agent workflow nodes with injected retrieval and LLM dependencies."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_client: LLMClient,
        *,
        config: Any,
        retrieval_tool: RetrievalTool | None = None,
        summarizer_tool: SummarizerTool | None = None,
        web_search_tool: WebSearchTool | None = None,
    ) -> None:
        self._retrieval = retrieval_tool or RetrievalTool(retrieval_service)
        self._summarizer = summarizer_tool or SummarizerTool(llm_client)
        self._web_search = web_search_tool or WebSearchTool()
        self._llm = llm_client
        self._config = config

    async def intent_node(self, state: AgentState) -> dict[str, Any]:
        explicit = state.get("intent")
        if getattr(self._config, "enable_dynamic_intent", False):
            intent = await self._dynamic_intent(state["question"])
        else:
            intent = classify_by_rules(state["question"], explicit)
        if intent not in {"summarize", "qa", "compare", "generate"}:
            intent = getattr(self._config, "default_intent", "qa")
        return {"intent": intent}

    async def retrieval_node(self, state: AgentState) -> dict[str, Any]:
        if not state.get("resource_ids"):
            return {"retrieved_chunks": [], "citations": []}
        try:
            chunks = await self._retrieval.invoke(
                question=state["question"],
                user_id=state["user_id"],
                resource_ids=state.get("resource_ids", []),
                top_k=state.get("top_k"),
                score_threshold=state.get("score_threshold"),
                max_context_tokens=state.get("max_context_tokens"),
            )
        except RetrievalForbiddenError:
            raise
        except APIException as exc:
            logger.warning("retrieval failed: %s", exc.code)
            chunks = []
        except Exception:
            logger.exception("retrieval failed")
            chunks = []
        return {"retrieved_chunks": chunks, "citations": []}

    async def summarize_node(self, state: AgentState) -> dict[str, Any]:
        retrieval_update: dict[str, Any] = {}
        chunks = state.get("retrieved_chunks", [])
        if state.get("resource_ids") and not chunks:
            retrieval_update = await self.retrieval_node(state)
            chunks = retrieval_update.get("retrieved_chunks", [])
        try:
            answer = await self._summarizer.invoke(
                question=state["question"],
                chunks=chunks,
                temperature=state.get("temperature") or 0.3,
                max_tokens=state.get("max_tokens") or 1024,
            )
        except Exception:
            logger.exception("summarize failed")
            answer = getattr(self._config, "fallback_message", "抱歉，暂无法生成答案，请稍后重试")
        return {**retrieval_update, "draft_answer": answer}

    async def qa_node(self, state: AgentState) -> dict[str, Any]:
        answer = await self._collect_llm_answer(
            self._build_context_prompt(state, "请基于资料回答问题。")
        )
        return {"draft_answer": answer}

    async def compare_node(self, state: AgentState) -> dict[str, Any]:
        prompt = self._build_context_prompt(state, "请横向对比多个资源的核心结论。")
        answer = await self._collect_llm_answer(prompt)
        return {"draft_answer": answer}

    async def generate_node(self, state: AgentState) -> dict[str, Any]:
        prompt = state["question"]
        if state.get("enable_web_search") and getattr(self._config, "enable_web_search", False):
            try:
                results = await self._web_search.invoke(state["question"])
                if results:
                    prompt = f"{prompt}\n\n可选网络资料：{results}"
            except Exception:
                logger.warning("web search skipped after failure", exc_info=True)
        answer = await self._collect_llm_answer(prompt)
        return {"draft_answer": answer}

    async def validate_node(self, state: AgentState) -> dict[str, Any]:
        iterations = state.get("iterations", 0) + 1
        chunks = state.get("retrieved_chunks", [])
        citations = state.get("citations", [])
        passed = not citations or self._citations_traceable(citations, chunks)
        low_confidence = not passed and iterations >= getattr(self._config, "max_iterations", 3)
        return {
            "iterations": iterations,
            "validation_passed": passed or low_confidence,
            "low_confidence": low_confidence,
            "final_answer": state.get("draft_answer", ""),
        }

    async def stream_generation(self, state: AgentState, node: str) -> AsyncIterator[str]:
        prompt = state["question"]
        if node == "qa":
            prompt = self._build_context_prompt(state, "请基于资料回答问题。")
        elif node == "compare":
            prompt = self._build_context_prompt(state, "请横向对比多个资源的核心结论。")
        elif node == "generate":
            prompt = state["question"]
        elif node == "summarize":
            prompt = self._build_context_prompt(state, "请基于资料总结核心内容。")
        request = LLMRequest(
            messages=[Message(role="user", content=prompt)],
            temperature=state.get("temperature") or 0.7,
            max_tokens=state.get("max_tokens") or 2048,
        )
        async for chunk in self._llm.stream_complete(request):
            if chunk.delta:
                yield chunk.delta
            if chunk.finish_reason in {"stop", "error"}:
                break

    async def _dynamic_intent(self, question: str) -> str:
        prompt = (
            "将问题分类为 summarize、qa、compare、generate 之一，只输出类别。\n" f"问题：{question}"
        )
        response = self._llm.complete(
            LLMRequest(
                messages=[Message(role="user", content=prompt)], temperature=0.0, max_tokens=8
            )
        )
        return response.content.strip().lower()

    async def _collect_llm_answer(self, prompt: str) -> str:
        parts: list[str] = []
        try:
            async for chunk in self._llm.stream_complete(
                LLMRequest(
                    messages=[Message(role="user", content=prompt)],
                    temperature=0.7,
                    max_tokens=2048,
                )
            ):
                if chunk.delta:
                    parts.append(chunk.delta)
                if chunk.finish_reason == "error":
                    return getattr(
                        self._config, "fallback_message", "抱歉，暂无法生成答案，请稍后重试"
                    )
                if chunk.finish_reason == "stop":
                    break
        except Exception:
            logger.exception("LLM generation failed")
            return getattr(self._config, "fallback_message", "抱歉，暂无法生成答案，请稍后重试")
        return "".join(parts)

    def _build_context_prompt(self, state: AgentState, instruction: str) -> str:
        chunks = state.get("retrieved_chunks", [])
        context = "\n\n".join(
            f"[^{idx + 1}] resource={chunk.resource_id} score={chunk.score}\n{chunk.text}"
            for idx, chunk in enumerate(chunks)
        )
        if not context:
            context = "无相关知识库上下文。"
        citation_rules = (
            "引用上下文片段时，请在句末使用 [^n] 标记，n 必须对应上下文片段序号；"
            "不得引用未提供的片段。"
        )
        return (
            f"{instruction}\n{citation_rules}\n\n"
            f"上下文：\n{context}\n\n用户问题：{state['question']}"
        )

    def _citations_traceable(
        self, citations: list[dict[str, Any]], chunks: list[RetrievalChunk]
    ) -> bool:
        resource_ids = {chunk.resource_id for chunk in chunks}
        return all(citation.get("resource_id") in resource_ids for citation in citations)
