# PRD：[S4-4] 使用 LangGraph 搭建 Agent 工作流

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)、[PRD_S3-5_glm4_kimi_llm.md](./PRD_S3-5_glm4_kimi_llm.md)、[PRD_S3-6_sse_qa_api.md](./PRD_S3-6_sse_qa_api.md)、[PRD_S3-8_conversation_persistence.md](./PRD_S3-8_conversation_persistence.md)、[PRD_S4-8_web_search_tool.md](./PRD_S4-8_web_search_tool.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-4 |
| **任务名称** | 使用 LangGraph 搭建 Agent 工作流 |
| **所属史诗** | E9 Agent 工作流 |
| **故事点** | 8 |
| **优先级** | Should |
| **依赖** | S3-4 向量检索+上下文组装、S3-5 接入智谱 GLM-4/Kimi |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为知识库用户，我希望助手能够根据我的提问意图自动选择最合适的处理路径（总结、问答、多资源对比、自由生成），并通过可见的步骤进度与流式答案获得更精准、可追溯的回答，以便在复杂问题场景下得到比固定 RAG 链路更高质量的结果。本任务使用 LangGraph 在 AI Service 中搭建可编排、可持久化、可流式输出的 Agent 工作流，替代 S3 阶段固定的“检索 → 上下文 → LLM”线性链路，为后续工具扩展（如 S4-8 Web 搜索）提供统一编排底座。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供 `POST /ai/v1/agent/run` 接口，使用 `X-Internal-Key` 认证，响应以 SSE 流式返回，由 Gateway 转发至客户端
- [ ] **AC-2** 使用 LangGraph `StateGraph` 搭建工作流，状态（`AgentState`）至少包含 `messages`、`intent`、`retrieved_chunks`、`draft_answer`、`citations`、`iterations`
- [ ] **AC-3** 意图识别节点支持 `summarize`、`qa`、`compare`、`generate` 四类意图；首期以固定路由（if-else by intent）实现，预留 LLM 动态意图识别升级路径
- [ ] **AC-4** 条件路由（`add_conditional_edges`）根据 `intent` 将流程分发到对应分支节点
- [ ] **AC-5** 检索节点调用 S3-4 `RetrievalService` 获取相关块；生成节点调用 S3-5 `LLMClient` 进行流式生成
- [ ] **AC-6** 对比（compare）分支支持多资源检索结果聚合，生成横向对比答案
- [ ] **AC-7** 校验节点对草稿答案进行幻觉/引用校验：引用必须可追溯到 `retrieved_chunks`，校验失败时回退重试或标注
- [ ] **AC-8** 通过 S3-6 SSE 输出节点进度事件（`node_start`/`node_end`）与最终答案流式 token（`chunk`），并以 `citation`、`done`、`error` 收尾
- [ ] **AC-9** 使用 LangGraph Checkpointer 持久化工作流状态，与 S3-8 会话/消息结合，支持按 `thread_id`（conversation_id）恢复中断执行
- [ ] **AC-10** 配置 `recursion_limit` / `max_iterations` 防止死循环；单个工具/节点失败时降级返回固定回复，不中断整条流
- [ ] **AC-11** 权限校验：校验 `X-Internal-Key`，并按 `user_id` + `resource_ids` 过滤，越权返回 403
- [ ] **AC-12** 将 S4-8 `web_search` 作为可选工具节点接入，配置开关控制是否启用
- [ ] **AC-13** 单元/集成测试覆盖率 80%+，覆盖意图识别、路由、各分支节点、状态持久化、迭代上限与降级

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py                 # StateGraph 构建与编译
│   │   ├── state.py                 # AgentState 定义
│   │   ├── router.py                # 条件路由（意图分发）
│   │   ├── checkpointer.py          # 状态持久化（与 S3-8 结合）
│   │   ├── runner.py                # 流式执行器：驱动 graph 并产出 SSE 事件
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── intent_node.py       # 意图识别（固定路由 + LLM 动态识别）
│   │   │   ├── retrieval_node.py    # 检索（调用 S3-4）
│   │   │   ├── summarize_node.py    # 总结分支
│   │   │   ├── compare_node.py      # 多资源对比分支
│   │   │   ├── generate_node.py     # 自由生成分支
│   │   │   ├── qa_node.py           # 问答分支（检索 + 生成）
│   │   │   ├── validate_node.py     # 幻觉/引用校验
│   │   │   └── web_search_node.py   # 可选：S4-8 Web 搜索工具节点
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── retrieval_tool.py    # retrieval_tool 封装
│   │       ├── summarizer_tool.py   # summarizer_tool 封装
│   │       └── web_search_tool.py   # web_search 工具封装
│   ├── api/
│   │   └── agent.py                 # POST /ai/v1/agent/run
│   └── models/
│       └── agent.py                 # AgentRunRequest / AgentStreamEvent
├── config/
│   └── ai.yaml
└── tests/
    ├── unit/test_agent_graph.py
    ├── unit/test_agent_nodes.py
    ├── unit/test_agent_router.py
    ├── unit/test_agent_checkpointer.py
    └── integration/test_agent_run_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| langgraph | 0.x | StateGraph 工作流编排、条件路由、Checkpointer |
| langchain-core | 0.x | 消息/工具基础抽象（仅基础类型，不引入其他 Agent 框架） |
| pydantic | 2.x | State 与请求/响应模型校验 |
| tenacity | 8.x | 节点/工具重试 |
| Flask 2.3+ / FastAPI 0.110+ | - | SSE 接口 |
| Celery | - | 异步任务（可选，长流程编排） |

> 说明：仅使用 `langgraph` + `langchain-core` 进行编排，不引入其他 Agent 框架；检索能力复用 S3-4 `RetrievalService`，LLM 能力复用 S3-5 `LLMClient`，不重复实现。

---

## 技术要点

### StateGraph 示例

```python
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState

graph_builder = StateGraph(AgentState)

graph_builder.add_node("intent", intent_node)
graph_builder.add_node("retrieve", retrieval_node)
graph_builder.add_node("summarize", summarize_node)
graph_builder.add_node("qa", qa_node)
graph_builder.add_node("compare", compare_node)
graph_builder.add_node("generate", generate_node)
graph_builder.add_node("validate", validate_node)

graph_builder.set_entry_point("intent")
graph_builder.add_conditional_edges(
    "intent",
    route_by_intent,                       # 返回分支名
    {
        "summarize": "summarize",
        "qa": "retrieve",
        "compare": "retrieve",
        "generate": "generate",
    },
)
graph_builder.add_edge("retrieve", "qa")   # qa 分支：检索后生成
graph_builder.add_edge("summarize", "validate")
graph_builder.add_edge("qa", "validate")
graph_builder.add_edge("compare", "validate")
graph_builder.add_edge("generate", "validate")
graph_builder.add_conditional_edges(
    "validate",
    route_after_validate,                  # 校验通过 -> END；失败且未超限 -> 重试
    {"pass": END, "retry": "retrieve"},
)

graph = graph_builder.compile(checkpointer=checkpointer)
```

### 节点/路由流程

1. **意图识别（intent）**：解析 `messages` 末尾用户问题，输出 `intent`（首期固定路由：按关键词/显式参数判断；二期由 LLM 分类）
2. **条件路由**：`route_by_intent(state)` 返回 `summarize` / `qa` / `compare` / `generate`
3. **检索（retrieve）**：调用 `retrieval_tool`（封装 S3-4），写入 `retrieved_chunks` 与 `citations`；`compare` 分支并发检索多个资源
4. **分支节点**：
   - `summarize`：对单资源调用 `summarizer_tool` 生成摘要
   - `qa`：基于上下文调用 `LLMClient.stream_complete` 生成答案
   - `compare`：聚合多资源结果，生成对比答案
   - `generate`：无检索，直接调用 LLM 自由生成
5. **校验（validate）**：校验草稿答案的引用可追溯性；失败且 `iterations < max_iterations` 则路由回 `retrieve` 重试，否则放行并标注
6. **结束**：`done` 事件携带最终答案与引用

### 错误处理与降级策略

- 意图无法识别：默认降级为 `qa` 分支
- 检索失败：写入空上下文，Prompt 提示“无相关知识”，继续生成通用回答
- LLM 调用失败：按 S3-5 重试/回退策略；仍失败则降级返回固定回复“抱歉，暂无法生成答案，请稍后重试”
- 校验反复失败：达到 `max_iterations` 后放行并附加 `low_confidence` 标记
- 工具失败（如 web_search）：跳过该工具节点，继续主流程
- 超时/死循环：`recursion_limit` 触发后返回 `error` 事件并保留已生成内容

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LangGraph 与现有异步 LLM 流式集成复杂 | 流式输出不稳定 | 分段联调：节点单测 → graph 集成 → SSE 端到端 |
| LLM 动态意图识别准确率不足 | 路由错误导致答案质量差 | 先固定路由上线，积累样本后再切 LLM 动态识别 |
| Checkpointer 与 S3-8 会话模型对齐成本 | 状态恢复不一致 | 以 `conversation_id` 作为 `thread_id`，状态快照写入 S3-8 metadata |
| 节点重试导致 token 成本上升 | 成本超预期 | 限制 `max_iterations`，重试仅作用于校验失败分支 |
| 多资源对比检索并发控制 | 资源/向量库压力 | 限制并发数（默认 3），超时降级为串行 |

---

## Web 端适配

- Agent 工作流接口为 AI Service 内部接口（`X-Internal-Key`），Web 端不直接访问
- Gateway 将 `POST /api/v1/conversations/{id}/ask` 转发至 `POST /ai/v1/agent/run`，并以 SSE 透传 `node_start`/`node_end`/`chunk`/`citation`/`done`/`error` 事件
- Web 端可基于 `node_start`/`node_end` 事件渲染“正在检索/正在生成/正在校验”等步骤进度
- 最终答案 token 与引用渲染复用 S3-6 / S3-7 的 SSE 解析与对话组件

---

## 备注

- 本任务为 Sprint 4 最大卡片（8 点），建议拆分为“骨架与固定路由”“流式与持久化”“校验与可选工具”三个子阶段逐步交付
- `AgentState` 设计为不可变更新（LangGraph 通过 reducer 合并），遵循项目 immutability 规范
- 节点均为纯函数（`state -> state`），便于单测与替换
- `recursion_limit`、`max_iterations`、`temperature` 等参数全部走配置，便于 A/B 调优
- 工具节点（retrieval/summarizer/web_search）采用统一 `Tool` 接口，为 S5 多工具扩展预留
