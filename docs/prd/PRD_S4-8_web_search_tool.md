# PRD：[S4-8] 接入 Web Search 工具（可选）

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S4-4_langgraph_agent_workflow.md](./PRD_S4-4_langgraph_agent_workflow.md)、[PRD_S3-5_glm4_kimi_llm.md](./PRD_S3-5_glm4_kimi_llm.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-8 |
| **任务名称** | 接入 Web Search 工具（可选） |
| **所属史诗** | E9 Agent 工作流 |
| **故事点** | 3 |
| **优先级** | Could |
| **依赖** | S4-4 LangGraph Agent 工作流、S3-5 智谱 GLM-4 / Kimi 生成答案 |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为知识库助手用户，我希望当知识库内文档不足以回答我的问题时，Agent 能够自动调用 Web Search 工具补充外部信息，并将搜索结果经 LLM 摘要后纳入答案上下文，同时明确区分「网络来源」与「文档来源」，以便我获得更完整的回答并清楚了解信息出处。本任务为 S4-4 LangGraph Agent 工作流提供一个可插拔的 Web Search 工具节点，支持 Serper 或 Bing Search API（可配置切换），API Key 仅通过环境变量注入，具备限流、超时与失败降级能力，失败时返回空结果而不阻塞 Agent 主流程。

---

## 验收标准（AC）

- [ ] **AC-1** 提供 `web_search(query, top_k)` 工具接口，返回 `[{title, url, snippet}]` 结构化结果列表
- [ ] **AC-2** 支持 Serper（默认）与 Bing Search API 两种 provider，通过配置切换
- [ ] **AC-3** 工具以 LangGraph 工具节点接入（langchain `@tool` 装饰器），由 Agent 决定是否调用
- [ ] **AC-4** 搜索结果由 LLM 摘要后纳入上下文，作为补充信息参与答案生成
- [ ] **AC-5** 具备限流（默认每分钟 20 次）、超时（默认 10s）、结果数控制（top_k 默认 5，上限 10）
- [ ] **AC-6** 搜索调用失败时降级返回空结果列表，不抛异常、不阻塞 Agent 主流程，并记录 WARN 日志
- [ ] **AC-7** 区分 web 来源与文档来源：web 内容不作为文档引用，单独标注「网络来源」并在上下文中以独立段落呈现
- [ ] **AC-8** API Key 通过环境变量注入（`SERPER_API_KEY` / `BING_API_KEY`），代码中不保留任何密钥，缺失时启动报错
- [ ] **AC-9** 提供内部测试端点 `POST /ai/v1/tools/web-search`（`X-Internal-Key` 认证）便于手工验证，生产链路为 Agent 内部工具调用
- [ ] **AC-10** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── agent/
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── web_search_tool.py      # @tool 装饰器封装 + LangGraph 节点
│   │       ├── base_search_provider.py # 抽象 provider
│   │       ├── serper_provider.py      # Serper API 实现
│   │       ├── bing_provider.py        # Bing Search API 实现
│   │       └── mock_provider.py        # 本地 mock，CI/开发使用
│   ├── models/
│   │   ├── web_search_request.py       # WebSearchRequest
│   │   └── web_search_result.py        # WebSearchResult / WebSearchResponse
│   └── api/
│       └── web_search_route.py         # POST /ai/v1/tools/web-search 测试端点
├── config/
│   └── ai.yaml                         # web_search 配置段
└── tests/
    ├── unit/test_web_search_tool.py
    ├── unit/test_serper_provider.py
    ├── unit/test_bing_provider.py
    └── integration/test_web_search_agent.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| httpx | 0.27.x | 异步 HTTP 调用 Serper / Bing API |
| langgraph | 0.x | Agent 工作流工具节点接入 |
| langchain-core | 0.x | `@tool` 装饰器与工具签名 |
| tenacity | 8.x | 搜索调用重试策略 |
| pydantic | 2.x | 请求/响应模型校验 |
| zhipuai | 2.x | GLM-4 摘要搜索结果 |

---

## 技术要点

### 工具调用示例

LangGraph Agent 在知识库检索不足时触发 `web_search` 工具调用，请求与响应示例如下：

```json
{
  "tool": "web_search",
  "args": {
    "query": "2026 年大模型推理优化最新进展",
    "top_k": 5
  }
}
```

```json
{
  "results": [
    {
      "title": "大模型推理加速技术综述",
      "url": "https://example.com/llm-inference",
      "snippet": "本文总结了 KV Cache、量化与投机解码等推理优化方向..."
    }
  ],
  "source_type": "web",
  "fallback": false
}
```

### 流程步骤

1. S4-4 LangGraph Agent 执行知识库检索（S3-4），评估上下文是否足以回答
2. 当知识库不足时，Agent 决定调用 `web_search` 工具，传入 `query` 与 `top_k`
3. `WebSearchTool` 根据配置选择 provider（Serper / Bing），发起 HTTP 请求
4. provider 解析返回结果，提取 `title`、`url`、`snippet`，组装为 `WebSearchResult` 列表
5. 搜索结果经 GLM-4 摘要后，以「网络来源」独立段落注入 Agent 上下文
6. Agent 综合文档上下文与网络来源生成最终答案，答案中 web 内容标注「网络来源」而非文档引用

### 错误处理与降级策略

- API Key 缺失：启动时报错，拒绝启动
- 搜索 API 超时：返回空结果列表，`fallback=true`，记录 WARN 日志，Agent 继续基于已有上下文作答
- 搜索 API 限流（429）：触发 tenacity 指数退避重试（最多 2 次），仍失败则降级返回空
- 结果解析异常：跳过异常条目，返回已解析的有效结果；全量异常则返回空
- Agent 调用工具异常：工具节点捕获所有异常并返回空结果，不向 Agent 抛错，保证主流程不中断

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Serper / Bing API 限流或不可用 | 搜索结果缺失 | 重试 + 降级返回空，Agent 仍可基于知识库作答 |
| 搜索结果质量不稳定 | 摘要引入噪声 | 限制 top_k、snippet 长度，LLM 摘要时标注不确定性 |
| Web 内容被误当作文档引用 | 引用溯源错乱 | 严格区分来源类型，web 结果不进入 S4-5 引用列表 |
| API Key 泄露 | 安全风险 | 仅环境变量注入，启动校验，禁止入库代码与日志 |

---

## Web 端适配

- Web Search 为 AI Service 内部工具，Web 端不直接调用搜索 API
- 搜索结果经 LLM 摘要后通过 S3-6 SSE 问答链路下发，Web 端在答案中可见「网络来源」标注段落
- 若 S4-5 引用溯源已上线，web 内容不生成 `citation` 事件，仅文档来源参与引用
- 测试端点 `POST /ai/v1/tools/web-search` 仅供后端联调，不对 Web 端开放

---

## 备注

- 本卡为 Could 优先级，排期紧张可延后至 Sprint 5；Agent 工作流在工具未就绪时应能跳过本工具正常运行
- 建议将 `WebSearchTool` 设计为可插拔工具，便于后续扩展更多外部信息源（如天气、股票）
- 搜索调用量与命中率建议接入监控，为后续 Prompt 调优与成本控制提供数据
- provider 切换通过配置实现，无需改动 Agent 代码
