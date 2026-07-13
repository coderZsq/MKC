from __future__ import annotations

from typing import Any

from app.agent.nodes import AgentNodes
from app.agent.router import route_after_validate, route_by_intent
from app.agent.state import AgentState


class AgentGraph:
    """Builds a LangGraph StateGraph when langgraph is installed."""

    def __init__(self, nodes: AgentNodes, checkpointer: Any = None) -> None:
        self.nodes = nodes
        self.checkpointer = checkpointer
        self.graph = self._build()

    def _build(self) -> Any | None:
        try:
            from langgraph.graph import END, StateGraph

            builder = StateGraph(AgentState)
            builder.add_node("intent", self.nodes.intent_node)
            builder.add_node("retrieve", self.nodes.retrieval_node)
            builder.add_node("summarize", self.nodes.summarize_node)
            builder.add_node("qa", self.nodes.qa_node)
            builder.add_node("compare", self.nodes.compare_node)
            builder.add_node("generate", self.nodes.generate_node)
            builder.add_node("validate", self.nodes.validate_node)
            builder.set_entry_point("intent")
            builder.add_conditional_edges(
                "intent",
                route_by_intent,
                {
                    "summarize": "summarize",
                    "qa": "retrieve",
                    "compare": "retrieve",
                    "generate": "generate",
                },
            )
            builder.add_conditional_edges(
                "retrieve",
                lambda state: "compare" if state.get("intent") == "compare" else "qa",
                {"qa": "qa", "compare": "compare"},
            )
            builder.add_edge("summarize", "validate")
            builder.add_edge("qa", "validate")
            builder.add_edge("compare", "validate")
            builder.add_edge("generate", "validate")
            builder.add_conditional_edges(
                "validate",
                route_after_validate,
                {"pass": END, "retry": "retrieve"},
            )
            saver = getattr(self.checkpointer, "saver", None)
            return builder.compile(checkpointer=saver)
        except Exception:
            return None
