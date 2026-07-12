# S4-8 测试用例：接入 Web Search 工具（可选）

## 1. 范围与目标

验证 AI Service Web Search 工具模块：`web_search` 工具接口、Serper / Bing provider、LangGraph 工具节点接入、LLM 摘要纳入上下文、限流/超时/结果数控制、失败降级、来源区分、API Key 环境变量管理与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- httpx 0.27.x
- langgraph 0.x
- langchain-core 0.x
- tenacity 8.x
- pydantic 2.x
- zhipuai 2.x（GLM-4 摘要）
- pytest, pytest-cov, respx（httpx mock）
- mock provider（本地开发 / CI）

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-8-001 | Functional | Unit | P0 | web_search 返回结构化结果列表 | 配置 provider=serper，mock HTTP 返回 | 调用 web_search(query, top_k=5) | 返回 WebSearchResponse，results 含 title/url/snippet | PRD AC-1 |
| MKC-TC-S4-8-002 | Functional | Unit | P0 | top_k 控制返回结果数 | mock 返回 10 条 | 调用 web_search(query, top_k=3) | results 长度 <= 3 | PRD AC-1、AC-5 |
| MKC-TC-S4-8-003 | Functional | Unit | P1 | 配置切换至 Bing provider | 配置 provider=bing | 调用 web_search | 使用 BingProvider 发起请求 | PRD AC-2 |
| MKC-TC-S4-8-004 | Functional | Unit | P1 | Serper provider 请求构建正确 | mock 拦截请求 | 调用 search | 请求头含 X-API-KEY，body 含 q 与 num | PRD AC-2 |
| MKC-TC-S4-8-005 | Functional | Unit | P1 | Bing provider 请求构建正确 | mock 拦截请求 | 调用 search | 请求头含 Ocp-Apim-Subscription-Key | PRD AC-2 |
| MKC-TC-S4-8-006 | Functional | Integration | P0 | LangGraph 工具节点可被 Agent 调用 | 注册 ToolNode | Agent 触发工具调用 | 工具被调用并返回结果 | PRD AC-3 |
| MKC-TC-S4-8-007 | Functional | Integration | P1 | Agent 自主决定是否调用 web_search | 知识库上下文充足 | Agent 推理 | 不调用 web_search 工具 | PRD AC-3 |
| MKC-TC-S4-8-008 | Functional | Unit | P1 | 搜索结果经 LLM 摘要纳入上下文 | mock 搜索与 LLM | 调用 summarize_and_inject | 返回含「网络来源」标注的摘要文本 | PRD AC-4 |
| MKC-TC-S4-8-009 | Functional | Unit | P1 | 搜索结果标注 source_type=web | 正常返回结果 | 检查 WebSearchResponse | source_type 为 "web" | PRD AC-7 |
| MKC-TC-S4-8-010 | Functional | Integration | P1 | web 内容不生成文档引用 | 搜索结果注入上下文 | 触发 S4-5 引用溯源 | citation 事件不含 web 来源 | PRD AC-7 |
| MKC-TC-S4-8-011 | Functional | Integration | P2 | mock provider 本地开发可用 | 配置 provider=mock | 调用 web_search | 返回固定结果列表 | PRD AC-2 |
| MKC-TC-S4-8-012 | Functional | Integration | P1 | 测试端点返回搜索结果 | 启动服务，带 X-Internal-Key | POST /ai/v1/tools/web-search | 返回 200 与 results | PRD AC-9 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-8-013 | Security | Integration | P0 | 测试端点缺少内部 Key 拒绝访问 | 请求头无 X-Internal-Key | POST /ai/v1/tools/web-search | 返回 401 | PRD AC-9、TECH 3 |
| MKC-TC-S4-8-014 | Security | Static | P0 | 无硬编码 API Key | 代码存在 | 全局搜索 SERPER/BING API Key | 仅 .env / 环境变量出现 | PRD AC-8 |
| MKC-TC-S4-8-015 | Security | Unit | P0 | API Key 缺失启动失败 | 未设置 SERPER_API_KEY | 启动服务 | 报错拒绝启动 | PRD AC-8 |
| MKC-TC-S4-8-016 | Security | Unit | P1 | API Key 不写入日志 | 正常调用搜索 | 检查日志输出 | 日志中无明文 API Key | PRD AC-8 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-8-017 | Negative | Unit | P0 | 搜索超时降级返回空 | mock httpx 超时 | 调用 web_search | 返回空 results，fallback=true | PRD AC-5、AC-6 |
| MKC-TC-S4-8-018 | Negative | Unit | P0 | 搜索失败不阻塞 Agent | mock provider 抛异常 | Agent 调用 web_search | 返回空结果，Agent 继续运行 | PRD AC-6 |
| MKC-TC-S4-8-019 | Negative | Unit | P1 | 限流触发拒绝调用 | 令牌桶耗尽 | 连续调用超阈值 | 第 21 次被限流，降级返回空 | PRD AC-5 |
| MKC-TC-S4-8-020 | Negative | Unit | P1 | 429 限流触发重试 | mock 返回 429 | 调用 web_search | 退避重试最多 2 次 | PRD AC-5、AC-6 |
| MKC-TC-S4-8-021 | Negative | Unit | P1 | 重试耗尽后降级 | mock 连续 429 | 调用 web_search | 返回空，fallback=true | PRD AC-6 |
| MKC-TC-S4-8-022 | Negative | Unit | P1 | query 为空校验失败 | 传入 query="" | 调用 web_search | 抛校验异常 / 测试端点 422 | PRD AC-1 |
| MKC-TC-S4-8-023 | Negative | Unit | P2 | top_k 超上限被截断 | 传入 top_k=99 | 调用 web_search | 实际使用 max_top_k=10 | PRD AC-5 |
| MKC-TC-S4-8-024 | Negative | Unit | P2 | 结果解析异常跳过异常条目 | mock 返回部分异常 JSON | 调用 _parse_response | 返回有效条目，跳过异常 | PRD AC-6 |
| MKC-TC-S4-8-025 | Negative | Integration | P1 | 搜索失败后 Agent 基于知识库作答 | mock 搜索失败 | Agent 完整流程 | 答案正常生成，无 web 来源 | PRD AC-6 |
| MKC-TC-S4-8-026 | Negative | Unit | P1 | API Key 无效降级 | mock 返回 401 | 调用 web_search | 降级返回空，fallback=true | PRD AC-6 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-8-027 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-10 |
| MKC-TC-S4-8-028 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |
| MKC-TC-S4-8-029 | Reliability | Static | P2 | 不可变数据模式校验 | 代码存在 | 静态审查 | 使用 pydantic 新建对象，无原地突变 | 工程规范 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-8-030 | Compatibility | Unit | P2 | Serper 与 Bing provider 接口一致 | 同一请求 | 分别调用 search | 返回相同 WebSearchResult 结构 | PRD AC-2 |
| MKC-TC-S4-8-031 | Performance | Integration | P2 | 单次搜索响应 < 10s | mock 延迟 | 调用 web_search | 在超时阈值内返回 | PRD AC-5 |
| MKC-TC-S4-8-032 | Performance | Integration | P2 | snippet 截断至配置长度 | mock 返回超长 snippet | 调用 _parse_response | snippet 长度 <= snippet_max_length | PRD AC-1 |
| MKC-TC-S4-8-033 | Reliability | Integration | P2 | 工具未就绪时 Agent 跳过 | 未注册 web_search 工具 | Agent 运行 | Agent 正常基于知识库作答 | PRD 备注 |

## 4. 测试执行清单

- [ ] web_search 工具接口与返回结构
- [ ] Serper / Bing / mock provider 切换
- [ ] LangGraph 工具节点接入与 Agent 自主调用
- [ ] LLM 摘要纳入上下文
- [ ] 限流、超时、top_k 控制
- [ ] 失败降级返回空，不阻塞 Agent
- [ ] 来源区分（web 不作为文档引用）
- [ ] API Key 环境变量注入，缺失启动失败
- [ ] 测试端点认证与权限
- [ ] 覆盖率 80%+
- [ ] ruff / mypy 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
