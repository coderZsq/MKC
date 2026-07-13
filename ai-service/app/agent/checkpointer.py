from __future__ import annotations

from typing import Any


class InMemoryAgentCheckpointer:
    """Small process-local checkpointer used by tests and local development."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}

    def save(self, thread_id: str, state: dict[str, Any]) -> None:
        self._states[thread_id] = dict(state)

    def load(self, thread_id: str) -> dict[str, Any] | None:
        state = self._states.get(thread_id)
        return dict(state) if state is not None else None


class AgentCheckpointer:
    """Build a LangGraph-compatible saver when available and keep local snapshots."""

    def __init__(self, backend: str = "memory", sqlite_path: str | None = None) -> None:
        self.backend = backend
        self.sqlite_path = sqlite_path
        self.local = InMemoryAgentCheckpointer()
        self.saver = self._build_saver()

    def _build_saver(self) -> Any | None:
        if self.backend == "memory":
            try:
                from langgraph.checkpoint.memory import MemorySaver

                return MemorySaver()
            except Exception:
                return None
        if self.backend == "sqlite" and self.sqlite_path:
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver

                return SqliteSaver.from_conn_string(self.sqlite_path)
            except Exception:
                return None
        return None

    def save(self, thread_id: str, state: dict[str, Any]) -> None:
        self.local.save(thread_id, state)

    def load(self, thread_id: str) -> dict[str, Any] | None:
        return self.local.load(thread_id)
