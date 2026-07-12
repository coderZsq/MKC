# 技术文档：[S4-4] 使用 LangGraph 搭建 Agent 工作流

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联 PRD：[../prd/PRD_S4-4_langgraph_agent_workflow.md](../prd/PRD_S4-4_langgraph_agent_workflow.md)
> 级别：AI 工程师

---

## 1. 文档目标

定义 AI Service 中基于 LangGraph 的 Agent 工作流的技术实现：StateGraph 编排、意图路由、各分支节点、工具集成、Checkpointer 状态持久化、SSE 流式输出、迭代上限与降级策略及测试方案，替代 S3 固定 RAG 链路。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- Celery（可选，长流程异步编排）
- langgraph 0.x（StateGraph、Checkpointer、条件路由）
- langchain-core 0.x（仅基础消息/工具类型，不引入其他 Agent 框架）
- pydantic 2.x（State 与模型校验）
- tenacity 8.x（节点/工具重试）
- 复用：S3-4 `RetrievalService`、S3-5 `LLMClient`、S3-6 SSE 格式化、S3-8 会话持久化

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/agent/run` | Internal API Key（`X-Internal-Key`） | 运行 Agent 工作流，SSE 流式返回 |

> Gateway 侧端点复用 S3-6 的 `POST /api/v1/conversations/{id}/ask`（Bearer JWT），由 Gateway 转发至本接口。

### 请求示例

```json
POST /ai/v1/agent/run
Headers: X-Internal-Key: <key>
Content-Type: application/json
{
  "question": "对比资源 A 与资源 B 的核心结论",
  "conversation_id": "conv-1",
  "message_id": "msg-1",
  "user_id": "user-1",
  "resource_ids": ["res-a", "res-b"],
  "history": [{"role": "user", "content": "上一次问题"}],
  "intent": "compare",
  "enable_web_search": false,
  "top_k": 5,
  "score_threshold": 0.7,
  "max_context_tokens": 4096,
  "temperature": 0.7,
  "max_tokens": 2048
}
```

### SSE 响应示例

```text
event: node_start
data: {"message_id":"msg-1","node":"intent","thread_id":"conv-1"}

event: node_end
data: {"message_id":"msg-1","node":"intent","intent":"compare"}

event: node_start
data: {"message_id":"msg-1","node":"retrieve","thread_id":"conv-1"}

event: node_end
data: {"message_id":"msg-1","node":"retrieve","chunks":3}

event: node_start
data: {"message_id":"msg-1","node":"compare"}

event: chunk
data: {"message_id":"msg-1","delta":"资源 A 侧重","index":0}

event: chunk
data: {"message_id":"msg-1","delta":"效率提升","index":1}

event: citation
data: {"message_id":"msg-1","resource_id":"res-a","score":0.89,"metadata":{"page":3}}

event: node_end
data: {"message_id":"msg-1","node":"validate","passed":true}

event: done
data: {"message_id":"msg-1","finish_reason":"stop","iterations":1,"low_confidence":false}

```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | INVALID_REQUEST | 缺少 question / conversation_id / user_id |
| 401 | UNAUTHORIZED | 缺少或无效 X-Internal-Key |
| 403 | FORBIDDEN | 无权访问 resource_ids |
| 408 | AGENT_TIMEOUT | 工作流整体超时 |
| 500 | AGENT_INTERNAL_ERROR | 节点未捕获异常 |
| 503 | AGENT_UNAVAILABLE | 依赖（检索/LLM）不可用且降级失败 |

---

## 4. 配置

新增 `config/ai.yaml` 段：

```yaml
agent:
  enabled: true
  recursion_limit: 12               # LangGraph 递归上限，防死循环
  max_iterations: 3                 # 校验失败最大重试次数
  overall_timeout: 120              # 整体超时（秒）
  default_intent: qa                # 意图无法识别时降级分支
  enable_dynamic_intent: false      # false=固定路由；true=LLM 动态识别
  dynamic_intent_model: glm-4-flash
  enable_web_search: false          # S4-8 工具开关
  compare_concurrency: 3            # 多资源对比检索并发数
  fallback_message: "抱歉，暂无法生成答案，请稍后重试"
  checkpointer:
    backend: sqlite                 # sqlite / redis（生产）
    redis_url: "${REDIS_URL}"
    sqlite_path: "data/agent_checkpoints.db"
  sse:
    emit_node_events: true          # 是否输出 node_start/node_end
```

---

## 5. 模块设计

### 5.1 AgentState（state.py）

```python
from typing import Annotated, TypedDict
from langgraph.graph import add_messages
from app.models.retrieval import Chunk

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]      # 对话消息（LangGraph reducer 合并）
    intent: str                                   # summarize/qa/compare/generate
    question: str
    user_id: str
    resource_ids: list[str]
    retrieved_chunks: list[Chunk]                 # 检索结果
    citations: list[dict]                         # 引用元数据
    draft_answer: str                             # 草稿答案
    final_answer: str                             # 校验后最终答案
    iterations: int                               # 当前迭代次数
    low_confidence: bool                          # 校验未通过但放行
    error: str | None                             # 节点级错误信息
```

### 5.2 AgentGraph（graph.py）

```python
class AgentGraph:
    """Builds and compiles the LangGraph StateGraph for the agent workflow."""

    def __init__(self, nodes: AgentNodes, checkpointer, config: AgentConfig) -> None:
        self._nodes = nodes
        self._checkpointer = checkpointer
        self._config = config
        self._graph = self._build()

    def _build(self):
        builder = StateGraph(AgentState)
        builder.add_node("intent", self._nodes.intent_node)
        builder.add_node("retrieve", self._nodes.retrieval_node)
        builder.add_node("summarize", self._nodes.summarize_node)
        builder.add_node("qa", self._nodes.qa_node)
        builder.add_node("compare", self._nodes.compare_node)
        builder.add_node("generate", self._nodes.generate_node)
        builder.add_node("validate", self._nodes.validate_node)
        builder.set_entry_point("intent")
        builder.add_conditional_edges("intent", route_by_intent, {...})
        builder.add_edge("retrieve", "qa")
        builder.add_edge("summarize", "validate")
        builder.add_edge("qa", "validate")
        builder.add_edge("compare", "validate")
        builder.add_edge("generate", "validate")
        builder.add_conditional_edges("validate", route_after_validate, {...})
        return builder.compile(checkpointer=self._checkpointer)

    async def astream(self, state: AgentState, thread_id: str) -> AsyncIterator:
        """Stream graph execution; yields state deltas for SSE rendering."""
        ...
```

### 5.3 Nodes（nodes/）

每个节点为纯函数 `async def node(state: AgentState) -> dict`，仅返回需更新的字段（不可变更新）。

```python
class AgentNodes:
    def __init__(self, retrieval_svc: RetrievalService,
                 llm_client: LLMClient, tools: AgentTools, config: AgentConfig) -> None: ...

    async def intent_node(self, state: AgentState) -> dict: ...
    async def retrieval_node(self, state: AgentState) -> dict: ...
    async def summarize_node(self, state: AgentState) -> dict: ...
    async def qa_node(self, state: AgentState) -> dict: ...
    async def compare_node(self, state: AgentState) -> dict: ...
    async def generate_node(self, state: AgentState) -> dict: ...
    async def validate_node(self, state: AgentState) -> dict: ...
```

### 5.4 Tools（tools/）

```python
class RetrievalTool:
    def __init__(self, retrieval_svc: RetrievalService) -> None: ...
    async def invoke(self, question: str, user_id: str, resource_ids: list[str]) -> list[Chunk]: ...

class SummarizerTool:
    def __init__(self, llm_client: LLMClient) -> None: ...
    async def invoke(self, chunks: list[Chunk]) -> str: ...

class WebSearchTool:                            # S4-8 可选
    def __init__(self, web_search_client) -> None: ...
    async def invoke(self, query: str) -> list[dict]: ...
```

### 5.5 Checkpointer（checkpointer.py）

```python
class AgentCheckpointer:
    """Bridges LangGraph checkpointer with S3-8 conversation persistence."""

    def __init__(self, backend: str, config: AgentConfig) -> None:
        self._saver = self._build_saver(backend, config)

    def _build_saver(self, backend: str, config: AgentConfig):
        if backend == "redis":
            from langgraph.checkpoint.redis import RedisSaver
            return RedisSaver.from_conn_string(config.redis_url)
        from langgraph.checkpoint.sqlite import SqliteSaver
        return SqliteSaver.from_path(config.sqlite_path)

    @property
    def saver(self):
        return self._saver
```

### 5.6 Runner（runner.py）

```python
class AgentRunner:
    """Drives graph execution and maps state deltas to SSE events."""

    def __init__(self, graph: AgentGraph, config: AgentConfig) -> None: ...

    async def run_stream(self, request: AgentRunRequest) -> AsyncIterator[AgentStreamEvent]:
        """Yield node_start/node_end/chunk/citation/done/error events."""
        ...
```

---

## 6. 关键代码实现

### 6.1 StateGraph 构建与 add_node

```python
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.router import route_by_intent, route_after_validate

def build_graph(nodes: AgentNodes, checkpointer, config: AgentConfig):
    builder = StateGraph(AgentState)

    builder.add_node("intent", nodes.intent_node)
    builder.add_node("retrieve", nodes.retrieval_node)
    builder.add_node("summarize", nodes.summarize_node)
    builder.add_node("qa", nodes.qa_node)
    builder.add_node("compare", nodes.compare_node)
    builder.add_node("generate", nodes.generate_node)
    builder.add_node("validate", nodes.validate_node)

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
    builder.add_edge("retrieve", "qa")
    builder.add_edge("summarize", "validate")
    builder.add_edge("qa", "validate")
    builder.add_edge("compare", "validate")
    builder.add_edge("generate", "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {"pass": END, "retry": "retrieve"},
    )

    return builder.compile(
        checkpointer=checkpointer,
        recursion_limit=config.recursion_limit,
    )
```

### 6.2 条件路由

```python
def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "qa")
    if intent not in {"summarize", "qa", "compare", "generate"}:
        return "qa"            # 降级为 qa
    return intent

def route_after_validate(state: AgentState) -> str:
    iterations = state.get("iterations", 0)
    max_iter = state.get("max_iterations", 3)
    passed = state.get("validation_passed", True)
    if passed or iterations >= max_iter:
        return "pass"
    return "retry"
```

### 6.3 意图识别节点（固定路由 + LLM 动态识别）

```python
async def intent_node(state: AgentState) -> dict:
    question = state["question"]
    if config.enable_dynamic_intent:
        intent = await llm_classify_intent(question)   # LLM 动态识别
    else:
        intent = classify_by_rules(question)           # 固定路由：关键词/显式参数
    if intent not in {"summarize", "qa", "compare", "generate"}:
        intent = config.default_intent                 # 降级
    return {"intent": intent}
```

### 6.4 检索节点（复用 S3-4）

```python
async def retrieval_node(state: AgentState) -> dict:
    try:
        chunks = await retrieval_tool.invoke(
            question=state["question"],
            user_id=state["user_id"],
            resource_ids=state["resource_ids"],
        )
    except APIException:
        logger.exception("retrieval failed")
        chunks = []                                     # 降级：空上下文
    citations = [{"resource_id": c.resource_id, "score": c.score,
                  "metadata": c.metadata} for c in chunks]
    return {"retrieved_chunks": chunks, "citations": citations}
```

### 6.5 QA 节点流式生成（复用 S3-5）

```python
async def qa_node(state: AgentState) -> dict:
    prompt = prompt_builder.build(state["retrieved_chunks"], state["question"])
    draft = []
    async for chunk in llm_client.stream_complete(
        LLMRequest(messages=[Message(role="user", content=prompt)],
                   temperature=state.get("temperature", 0.7),
                   max_tokens=state.get("max_tokens", 2048))
    ):
        if chunk.delta:
            draft.append(chunk.delta)
            # 由 Runner 捕获并产出 SSE chunk 事件
    return {"draft_answer": "".join(draft)}
```

### 6.6 校验节点（幻觉/引用校验）

```python
async def validate_node(state: AgentState) -> dict:
    iterations = state.get("iterations", 0) + 1
    passed = citations_traceable(state["draft_answer"], state["citations"])
    low_confidence = not passed and iterations >= config.max_iterations
    return {
        "iterations": iterations,
        "validation_passed": passed or low_confidence,
        "low_confidence": low_confidence,
        "final_answer": state["draft_answer"],
    }
```

### 6.7 Runner 流式产出 SSE

```python
async def run_stream(self, request: AgentRunRequest) -> AsyncIterator[AgentStreamEvent]:
    state = build_initial_state(request)
    config = {"configurable": {"thread_id": request.conversation_id},
              "recursion_limit": self._config.recursion_limit}
    try:
        async for event in self._graph.astream(state, config=config, stream_mode="updates"):
            for node_name, update in event.items():
                yield AgentStreamEvent("node_end", {"node": node_name, ...})
                if "draft_answer" in update:
                    yield AgentStreamEvent("chunk", {"delta": update["draft_answer"]})
        yield AgentStreamEvent("done", {"finish_reason": "stop"})
    except RecursionError:
        yield AgentStreamEvent("error", {"error_code": "AGENT_TIMEOUT",
                                         "message": "达到迭代上限"})
    except APIException as exc:
        yield AgentStreamEvent("error", {"error_code": exc.code, "message": exc.message})
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 缺少 question/conversation_id/user_id | 400 | INVALID_REQUEST | 参数校验失败 |
| 缺少/无效 X-Internal-Key | 401 | UNAUTHORIZED | 未授权访问 |
| resource_ids 越权 | 403 | FORBIDDEN | 无权访问资源 |
| 意图无法识别 | 200 | - | 降级为 default_intent，继续执行 |
| 检索失败 | 200 | - | 空上下文，继续生成通用回答 |
| LLM 调用失败 | 200 | - | 降级返回 fallback_message |
| 校验反复失败 | 200 | - | 放行并标注 low_confidence |
| 达到 recursion_limit | 408 | AGENT_TIMEOUT | 达到迭代上限 |
| 节点未捕获异常 | 500 | AGENT_INTERNAL_ERROR | 内部错误 |
| 依赖全不可用 | 503 | AGENT_UNAVAILABLE | Agent 不可用 |

> 流式场景下错误以 `error` SSE 事件返回，HTTP 状态在首字节前尽可能设置；已开始流式后则通过 `error` 事件结束流。

---

## 8. Web 端适配要点

- Gateway 将 `POST /api/v1/conversations/{id}/ask`（Bearer JWT）转发至 `POST /ai/v1/agent/run`（`X-Internal-Key`），透传 SSE 事件
- Web 端基于 `node_start`/`node_end` 事件渲染步骤进度（检索中/生成中/校验中）
- `chunk`/`citation`/`done`/`error` 事件复用 S3-6 / S3-7 的 SSE 解析与对话组件
- `low_confidence` 标记由 Web 端以提示样式展示
- 浏览器 `EventSource` 通过 `?token=` 传 JWT，Gateway 配置 CORS 与 `X-Accel-Buffering: no`

---

## 9. 测试策略

- **单元测试**：`route_by_intent` / `route_after_validate` 路由逻辑；各节点纯函数（mock RetrievalService / LLMClient / Tools）；`intent_node` 固定路由与动态识别；`validate_node` 引用校验与迭代计数；Checkpointer saver 选择
- **集成测试**：`AgentGraph` 端到端（mock 依赖）验证各分支路径与状态流转；`POST /ai/v1/agent/run` SSE 事件序列；`recursion_limit` 触发降级；Checkpointer 按 `thread_id` 恢复
- **Mock 策略**：固定 LLM 流式 chunk 序列、固定检索结果，断言节点更新与 SSE 事件
- **覆盖率目标**：80%+，覆盖路由、节点、降级、迭代上限、权限校验

---

## 10. 检查清单

- [ ] `AgentState` 定义含全部必填字段
- [ ] `StateGraph` 构建与 `add_node` / `add_conditional_edges`
- [ ] 四类意图固定路由 + LLM 动态识别开关
- [ ] 检索节点复用 S3-4 `RetrievalService`
- [ ] 生成节点复用 S3-5 `LLMClient.stream_complete`
- [ ] 对比分支多资源聚合
- [ ] 校验节点幻觉/引用校验与迭代重试
- [ ] Checkpointer 持久化与 S3-8 `thread_id` 对齐
- [ ] `recursion_limit` / `max_iterations` 防死循环
- [ ] 工具失败降级返回固定回复
- [ ] SSE 事件 `node_start`/`node_end`/`chunk`/`citation`/`done`/`error`
- [ ] `X-Internal-Key` 与 resource 越权校验
- [ ] S4-8 `web_search` 可选工具节点开关
- [ ] 测试覆盖率 80%+
- [ ] ruff / mypy 通过，无硬编码密钥
- [ ] OpenAPI / 文档同步更新
