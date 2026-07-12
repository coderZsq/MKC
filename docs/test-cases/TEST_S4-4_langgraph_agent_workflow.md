# S4-4 测试用例：使用 LangGraph 搭建 Agent 工作流

## 1. 范围与目标

验证 AI Service 中基于 LangGraph 的 Agent 工作流：StateGraph 编排、意图识别、条件路由、各分支节点（检索/总结/问答/对比/生成/校验）、工具集成、Checkpointer 状态持久化、SSE 流式输出、迭代上限与降级、权限校验及测试覆盖率。

## 2. 测试环境

- Python 3.11+
- langgraph 0.x + langchain-core 0.x
- pydantic 2.x、tenacity 8.x
- pytest、pytest-cov、pytest-asyncio
- mock RetrievalService / LLMClient / Tools

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-4-001 | Functional | Integration | P0 | Agent run 接口返回 SSE 流 | 依赖 mock 就绪 | POST /ai/v1/agent/run（带 X-Internal-Key） | 返回 text/event-stream，含 node_start/chunk/done 事件 | PRD AC-1 |
| MKC-TC-S4-4-002 | Functional | Unit | P0 | AgentState 含全部必填字段 | 定义 state | 构造 AgentState 并校验 | 含 messages/intent/retrieved_chunks/draft_answer/citations/iterations | PRD AC-2 |
| MKC-TC-S4-4-003 | Functional | Unit | P0 | 意图识别支持四类意图 | intent_node 就绪 | 分别输入 summarize/qa/compare/generate 触发问题 | 输出对应 intent 值 | PRD AC-3 |
| MKC-TC-S4-4-004 | Functional | Unit | P1 | 固定路由按关键词/参数判断 intent | enable_dynamic_intent=false | 调用 intent_node | 走规则分类，未启用 LLM | PRD AC-3 |
| MKC-TC-S4-4-005 | Functional | Unit | P0 | 条件路由 route_by_intent 分发 | graph 编译完成 | 对各 intent 调用 route_by_intent | 返回对应分支名，非法值降级为 qa | PRD AC-4 |
| MKC-TC-S4-4-006 | Functional | Unit | P0 | 检索节点调用 S3-4 RetrievalService | mock RetrievalService | 执行 retrieval_node | 调用 retrieval_tool.invoke 并写入 retrieved_chunks/citations | PRD AC-5 |
| MKC-TC-S4-4-007 | Functional | Unit | P0 | 生成节点调用 S3-5 LLMClient 流式生成 | mock LLMClient | 执行 qa_node | 调用 stream_complete 并拼接 draft_answer | PRD AC-5 |
| MKC-TC-S4-4-008 | Functional | Integration | P1 | 对比分支多资源聚合 | 提供 res-a/res-b | intent=compare 执行 retrieve+compare | 并发检索多资源并生成对比答案 | PRD AC-6 |
| MKC-TC-S4-4-009 | Functional | Unit | P1 | 校验节点引用可追溯 | 提供 draft 与 citations | 执行 validate_node | 引用可追溯到 retrieved_chunks 时 passed=true | PRD AC-7 |
| MKC-TC-S4-4-010 | Functional | Unit | P1 | 校验失败未超限触发重试 | iterations < max | 执行 validate_node | 路由返回 retry 回 retrieve | PRD AC-7 |
| MKC-TC-S4-4-011 | Functional | Integration | P0 | SSE 输出节点进度与 token 事件 | Runner 就绪 | 执行 run_stream | 产出 node_start/node_end/chunk/citation/done 事件 | PRD AC-8 |
| MKC-TC-S4-4-012 | Functional | Integration | P1 | Checkpointer 按 thread_id 恢复 | 持久化状态存在 | 以相同 conversation_id 再次执行 | 从断点恢复或读取历史状态 | PRD AC-9 |
| MKC-TC-S4-4-013 | Functional | Unit | P1 | LLM 动态意图识别开关 | enable_dynamic_intent=true | 调用 intent_node | 走 LLM 分类路径 | PRD AC-3 |
| MKC-TC-S4-4-014 | Functional | Unit | P1 | 总结分支调用 summarizer_tool | mock SummarizerTool | intent=summarize 执行 summarize_node | 调用 summarizer_tool 生成摘要 | PRD AC-5 |
| MKC-TC-S4-4-015 | Functional | Unit | P2 | 自由生成分支无检索直连 LLM | mock LLMClient | intent=generate 执行 generate_node | 不调用检索，直接 stream_complete | PRD AC-5 |
| MKC-TC-S4-4-016 | Functional | Integration | P2 | web_search 可选工具节点开关 | enable_web_search=true/false | 执行工作流 | 开启时接入 web_search_node，关闭时跳过 | PRD AC-12 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-4-017 | Security | Integration | P0 | 缺少 X-Internal-Key 拒绝访问 | 请求头无 Key | POST /ai/v1/agent/run | 返回 401 UNAUTHORIZED | PRD AC-11 |
| MKC-TC-S4-4-018 | Security | Integration | P0 | 无效 X-Internal-Key 拒绝访问 | Key 错误 | POST /ai/v1/agent/run | 返回 401 UNAUTHORIZED | PRD AC-11 |
| MKC-TC-S4-4-019 | Security | Unit | P1 | 越权 resource_ids 返回 403 | 传入他人 resource_id | 调用 retrieval_node | 返回 403 FORBIDDEN | PRD AC-11 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-4-020 | Negative | Integration | P0 | 缺少 question 返回 400 | 请求无 question | POST /ai/v1/agent/run | 返回 INVALID_REQUEST | PRD AC-1 |
| MKC-TC-S4-4-021 | Negative | Unit | P1 | 意图无法识别降级为 default_intent | 输入无法分类问题 | 调用 intent_node | intent 降级为 config.default_intent | PRD AC-10 |
| MKC-TC-S4-4-022 | Negative | Unit | P1 | 检索失败降级空上下文 | mock RetrievalService 抛异常 | 执行 retrieval_node | chunks 为空，继续流程 | PRD AC-10 |
| MKC-TC-S4-4-023 | Negative | Unit | P1 | LLM 失败降级固定回复 | mock LLMClient 抛异常 | 执行 qa_node | 返回 fallback_message | PRD AC-10 |
| MKC-TC-S4-4-024 | Negative | Unit | P1 | 校验反复失败达上限放行标注 | iterations >= max | 执行 validate_node | 放行并 low_confidence=true | PRD AC-10 |
| MKC-TC-S4-4-025 | Negative | Integration | P1 | 达到 recursion_limit 返回 AGENT_TIMEOUT | 模拟死循环重试 | 执行 run_stream | 产出 error 事件，error_code=AGENT_TIMEOUT | PRD AC-10 |
| MKC-TC-S4-4-026 | Negative | Integration | P1 | 工具失败跳过继续主流程 | mock web_search 抛异常 | 执行工作流 | 跳过该工具节点，主流程不中断 | PRD AC-10 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-4-027 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-13 |
| MKC-TC-S4-4-028 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |
| MKC-TC-S4-4-029 | Security | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 API Key | 仅 .env 出现 | 安全基线 |
| MKC-TC-S4-4-030 | Security | Static | P2 | API Key 仅环境变量注入 | 配置存在 | 检查配置加载 | key 来自 env，非字面量 | PRD AC-11 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-4-031 | Compatibility | Integration | P2 | SSE 事件格式与 S3-6 对齐 | S3-6 解析器可用 | 对比事件类型与字段 | chunk/citation/done/error 与 S3-6 一致 | PRD AC-8 |
| MKC-TC-S4-4-032 | Compatibility | Unit | P2 | Checkpointer 支持 sqlite/redis | 配置两种 backend | 切换 backend 构造 saver | 正确创建对应 saver | PRD AC-9 |
| MKC-TC-S4-4-033 | Performance | Unit | P2 | 单次工作流（mock）耗时 < 2s | mock 依赖 | 执行 run_stream | 端到端耗时 < 2s | 性能基线 |
| MKC-TC-S4-4-034 | Performance | Unit | P2 | 对比分支并发检索受控 | compare_concurrency=3 | 执行 compare 分支 | 并发数不超过配置上限 | PRD 阻塞风险 |

## 4. 测试执行清单

- [ ] Agent run SSE 接口端到端
- [ ] AgentState 字段完整性
- [ ] 意图识别（固定路由 + 动态识别）
- [ ] 条件路由分发与降级
- [ ] 检索/生成/总结/对比/校验节点
- [ ] SSE 节点进度与 token 事件
- [ ] Checkpointer 持久化与恢复
- [ ] recursion_limit / max_iterations 防死循环
- [ ] 检索/LLM/工具失败降级
- [ ] 权限校验与越权
- [ ] web_search 可选工具开关
- [ ] 覆盖率 80%+
- [ ] ruff / mypy 通过
- [ ] 无硬编码密钥
- [ ] SSE 格式与 S3-6 对齐

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
