from __future__ import annotations

from app.models.retrieval import RetrievalChunk
from app.services.llm.llm_client import LLMClient
from app.services.llm.models import LLMRequest, Message


class SummarizerTool:
    """Summarize retrieved chunks with the shared LLM client."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def invoke(
        self,
        *,
        question: str,
        chunks: list[RetrievalChunk],
        temperature: float = 0.3,
        max_tokens: int = 1024,
        memory_context: str = "",
    ) -> str:
        context = "\n\n".join(chunk.text for chunk in chunks) or "无可用上下文。"
        prompt = f"请基于以下材料回答用户的总结请求。\n\n材料：\n{context}\n\n请求：{question}"
        messages: list[Message] = []
        if memory_context:
            messages.append(Message(role="system", content=memory_context))
        messages.append(Message(role="user", content=prompt))
        parts: list[str] = []
        async for chunk in self._llm.stream_complete(
            LLMRequest(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        ):
            if chunk.delta:
                parts.append(chunk.delta)
            if chunk.finish_reason in {"stop", "error"}:
                break
        return "".join(parts)
