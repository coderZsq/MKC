# 敏捷排卡计划：多媒体 AI 知识库助手

> 版本：v1.0  
> 日期：2026-07-06  > 作者：朱双泉  > 基于 PRD：[PRD_multimedia_knowledge_assistant.md](./prd/PRD_multimedia_knowledge_assistant.md)

---

## 一、项目管理策略

### 1.1 迭代节奏

| 项 | 说明 |
|---|---|
| **Sprint 周期** | 2 周 |
| **总周期** | 6 个 Sprint（12 周），约 3 个月 |
| **每日站会** | 自组织 5 分钟，回答：昨天做了什么 / 今天做什么 / 遇到什么阻塞 |
| **Sprint 结束仪式** | Demo + 回顾（Retrospective） |
| **估算单位** | 故事点（Story Points），斐波那契数列：1、2、3、5、8、13 |

### 1.2 优先级原则

1. **MVP 优先**：先让「上传 → 转录/解析 → 问答」全链路跑通。
2. **可见性优先**：每个 Sprint 结束都有可演示的增量。
3. **基础设施前置**：Docker Compose、CI、数据库必须先搭好。
4. **优化后置**：复杂 Agent 工作流、评估体系、可观测性放在中后期。

### 1.3 单人项目看板结构

```
┌──────────────┬─────────────┬──────────────┬───────────────┬────────┐
│   Backlog    │   To Do     │ In Progress  │ Review / Test │  Done  │
│   待排期需求  │ 本 Sprint   │    进行中     │   自测/联调    │  完成   │
└──────────────┴─────────────┴──────────────┴───────────────┴────────┘
```

### 1.4 工具建议

| 用途 | 工具 |
|---|---|
| 看板 | GitHub Projects / Notion / Trello |
| 文档 | Notion / 飞书文档 / README |
| 代码 | GitHub |
| CI/CD | GitHub Actions |
| 时间追踪 | 番茄钟 / Clockify |

---

## 二、用户故事地图

### 2.1 核心用户活动

```
用户注册登录
    │
    ├── 上传 MP3 ──┬── 查看转录进度 ──┬── 查看 SRT ──┬── 与知识库对话
    │              │                   │               │
    └── 上传 PDF ──┴── 查看解析进度 ──┴── 查看文本 ──┴── 跨文档问答
```

### 2.2 史诗与用户故事

| 史诗（Epic） | 用户故事 | 优先级 | 目标 Sprint |
|---|---|---|---|
| **E1 用户认证** | 作为用户，我希望注册登录，以便安全使用我的知识库 | Must | S1 |
| **E2 文件上传** | 作为用户，我希望上传 MP3/PDF 文件，以便系统帮我处理 | Must | S1 |
| **E3 任务进度** | 作为用户，我希望看到处理进度，以便了解何时可用 | Must | S1 |
| **E4 音频转录** | 作为用户，我希望 MP3 自动转成 SRT 和文本，以便搜索和阅读 | Must | S2 |
| **E5 PDF 解析** | 作为用户，我希望 PDF 自动解析成结构化文本，以便检索 | Must | S2 |
| **E6 知识库检索** | 作为用户，我希望向知识库提问并获得带来源的答案 | Must | S3 |
| **E7 AI 对话** | 作为用户，我希望多轮对话并看到流式回复，以便高效学习 | Must | S3 |
| **E8 智能抽取** | 作为用户，我希望系统自动提取摘要/标签/章节，以便快速浏览 | Should | S4 |
| **E9 Agent 工作流** | 作为用户，我希望系统理解我是要总结/问答/对比，以便获得更精准的回答 | Should | S4 |
| **E10 评估优化** | 作为开发者，我希望评估 RAG 效果，以便持续优化 | Could | S5 |
| **E11 可观测性** | 作为开发者，我希望监控系统运行状态，以便排查问题 | Could | S5 |
| **E12 部署上线** | 作为开发者，我希望项目能部署到服务器并对外演示 | Should | S5 |

---

## 三、Sprint 排期

---

### Sprint 0：基础设施与项目骨架

**时间**：第 1-2 周  
**目标**：所有服务能本地一键启动，基础 CI 跑通。  
**交付物**：GitHub 仓库 + 本地 K8s 开发环境 + CI 流水线 + 三个服务骨架

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S0-1] 初始化 GitHub 仓库与目录结构 | 1 | 无 | `client/`、`gateway/`、`ai-service/`、`infra/`、`docs/` |
| [S0-2] 搭建本地 K8s 开发环境并编写 manifests | 5 | S0-1 | minikube/k3d + nginx-ingress-controller + MySQL + Redis + MinIO + Milvus + Jaeger + K8s YAML |
| [S0-3] 配置 GitHub Actions CI 流水线 | 2 | S0-1 | Python 测试、Go 测试、Flutter analyze |
| [S0-4] 设计数据库 Schema 并创建 migration | 2 | S0-1 | users/resources/tasks/conversations/messages |
| [S0-5] 设计 API 接口文档 | 2 | S0-4 | OpenAPI/Swagger 初稿 |
| [S0-6] 搭建 Flutter 项目骨架 | 2 | S0-1 | Clean Architecture + Riverpod + 路由 |
| [S0-7] 搭建 Go Gateway 项目骨架 | 2 | S0-1 | Gin + GORM + 配置管理 |
| [S0-8] 搭建 Python AI Service 项目骨架 | 2 | S0-1 | Flask + Celery + 配置管理 |
| **Sprint 0 总计** | **18** | | |

#### Sprint 0 Demo 检查清单

- [ ] `kubectl apply -f infra/k8s/` 能在本地 minikube/k3d 启动所有服务
- [ ] `kubectl get pods` 所有 Pod 状态 Running
- [ ] K8s Ingress 或 NodePort 能访问 Gateway 健康检查接口

---

### Sprint 1：用户认证 + 文件上传 + 任务状态

**时间**：第 3-4 周  
**目标**：用户能注册登录、上传文件、看到任务进度。  
**交付物**：注册登录 + 上传 MP3/PDF + 任务中心 + 实时进度

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S1-1] 实现用户注册/登录 API | 3 | S0-4 | JWT + Redis Session、密码哈希、Go Gateway |
| [S1-2] Flutter 登录/注册页面 | 2 | S1-1 | 表单校验、Token 本地存储 |
| [S1-3] 实现文件上传 API（支持分片） | 5 | S0-2, S0-4 | Go Gateway + MinIO |
| [S1-4] Flutter 文件选择与上传页 | 3 | S1-3 | 上传进度、队列管理 |
| [S1-5] 实现任务创建与状态查询 API | 3 | S0-4 | MySQL task 表、状态机 |
| [S1-6] Flutter 任务中心页面 | 3 | S1-5 | 任务列表、进度展示 |
| [S1-7] 实现 SSE/WebSocket 任务进度推送 | 3 | S1-5, S1-6 | Gateway → Flutter 实时进度 |
| **Sprint 1 总计** | **22** | | |

#### Sprint 1 Demo 检查清单

- [ ] 用户可注册登录
- [ ] 可选择 MP3/PDF 上传
- [ ] 上传后任务中心出现任务
- [ ] 任务状态实时更新（pending → processing → success）

---

### Sprint 2：MP3 转录 + PDF 解析

**时间**：第 5-6 周  
**目标**：上传的 MP3 能生成 SRT 和文本，PDF 能解析成文本。  
**交付物**：ASR 转录流水线 + PDF 解析流水线 + 内容查看页

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S2-1] 集成 faster-whisper 实现 ASR | 5 | S0-8 | 音频预处理、分片、转录 |
| [S2-2] 生成 SRT 字幕文件 | 2 | S2-1 | 时间戳对齐、SRT 格式输出 |
| [S2-3] 音频文本清洗（语气词/重复） | 3 | S2-2 | LLM 后处理 |
| [S2-4] 集成 pymupdf 实现 PDF 文本提取 | 3 | S0-8 | 文本、目录、页码 |
| [S2-5] PDF 扫描件 OCR（可选） | 2 | S2-4 | paddleocr |
| [S2-6] 存储转录/解析结果到对象存储和数据库 | 2 | S1-5 | SRT/文本文件存 MinIO，元数据存 PG |
| [S2-7] Flutter 内容查看页（SRT/文本） | 3 | S2-2, S2-4 | 字幕高亮、文本折叠 |
| [S2-8] 转录/解析任务异步执行与失败重试 | 3 | S1-5 | Celery Worker + 指数退避 |
| **Sprint 2 总计** | **23** | | |

#### Sprint 2 Demo 检查清单

- [ ] 上传 MP3 后自动生成 SRT
- [ ] 可查看清洗后的转录文本
- [ ] 上传 PDF 后解析出结构化文本
- [ ] 失败任务可手动重试

---

### Sprint 3：Embedding + 基础 RAG 问答

**时间**：第 7-8 周  
**目标**：用户能向已处理的文件提问，获得基于内容的答案。  
**交付物**：向量知识库 + SSE 流式问答 + 多轮对话

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S3-1] 文本分块策略实现 | 3 | S2-3, S2-4 | 按章节/语义/长度分块 |
| [S3-2] 集成 text-embedding-v3 生成 Embedding | 3 | S0-8 | 调用智谱 Embedding API |
| [S3-3] 集成 Milvus 向量存储 | 5 | S0-2 | 集合设计、索引、元数据过滤 |
| [S3-4] 实现向量检索 + 上下文组装 | 5 | S3-1, S3-3 | Top-K 召回、Prompt 构建 |
| [S3-5] 接入智谱 GLM-4 / Kimi 生成答案 | 3 | S0-8 | API 封装、流式输出 |
| [S3-6] 实现 SSE 问答 API | 5 | S1-7, S3-5 | Python → Go → Flutter 流式链路 |
| [S3-7] Flutter AI 对话页面 | 5 | S3-6 | Markdown 渲染、流式展示 |
| [S3-8] 会话与消息持久化 | 3 | S0-4 | 多轮上下文、历史记录 |
| **Sprint 3 总计** | **32** | | |

#### Sprint 3 Demo 检查清单

- [ ] 上传文件后能向知识库提问
- [ ] 答案基于文件内容
- [ ] 答案通过 SSE 流式输出
- [ ] 支持多轮对话和历史记录

---

### Sprint 4：Agent 工作流 + 智能抽取 + 溯源

**时间**：第 9-10 周  
**目标**：答案带引用溯源，系统自动摘要/标签/章节，Agent 理解不同意图。  
**交付物**：LangGraph Agent + 引用溯源 + 摘要标签

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S4-1] 实现全文/章节摘要提取 | 3 | S2-3, S2-4 | LLM 摘要 |
| [S4-2] 实现标签/实体抽取 | 3 | S2-3, S2-4 | 关键词、命名实体 |
| [S4-3] 资源卡片展示摘要与标签 | 2 | S4-1, S4-2 | Flutter 资源列表升级 |
| [S4-4] 使用 LangGraph 搭建 Agent 工作流 | 8 | S3-4, S3-5 | 意图识别、检索、总结、对比、生成、校验节点 |
| [S4-5] 答案引用溯源（时间戳/页码） | 5 | S3-4 | 引用格式化、Flutter 引用卡片 |
| [S4-6] 引用跳转：点击跳转到 SRT 时间戳 / PDF 页码 | 3 | S4-5 | 音频播放器跳转、PDF 文本定位 |
| [S4-7] 混合检索 + 重排序 | 5 | S3-4 | BM25 + 向量 + Cross-Encoder |
| [S4-8] 接入 Web Search 工具（可选） | 3 | S4-4 | Serper/Bing API |
| **Sprint 4 总计** | **32** | | |

#### Sprint 4 Demo 检查清单

- [ ] 资源卡片展示摘要和标签
- [ ] Agent 能处理总结/问答/对比等意图
- [ ] 答案带 [^1] [^2] 引用
- [ ] 点击引用可跳转到音频时间戳或 PDF 页码
- [ ] 混合检索效果优于纯向量检索

---

### Sprint 5：评估 + 可观测性 + 部署上线

**时间**：第 11-12 周  
**目标**：项目达到生产级可演示状态，部署上线。  
**交付物**：LLM-as-judge + 监控 + 部署 + 技术博客

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S5-1] 构建评估数据集 | 3 | S3-7 | 50-100 条问答对 |
| [S5-2] 实现 LLM-as-judge 评估流水线 | 5 | S5-1 | 召回率、忠实度、相关性、引用准确率 |
| [S5-3] 接入 OpenTelemetry 链路追踪 | 3 | S0-7, S0-8 | Gateway + AI Service Trace |
| [S5-4] 接入 Prometheus + Grafana 监控 | 3 | S0-2 | QPS、Latency、错误率看板 |
| [S5-5] 接入 LangSmith / Langfuse | 2 | S3-5 | LLM 调用观测 |
| [S5-6] 完善错误处理与降级策略 | 3 | S1-S4 | 超时、重试、异常提示 |
| [S5-7] 编写完整 README 与架构文档 | 2 | 全部 | 安装、部署、使用说明 |
| [S5-8] 部署到 Kubernetes 集群并绑定域名 | 5 | S0-2 | 云厂商 K8s / 自管集群 / Ingress / Cert-Manager |
| [S5-9] 编写技术博客/掘金文章 | 2 | S5-7 | 项目复盘，用于简历背书 |
| [S5-10] Flutter 多端适配检查 | 2 | S3-7 | iOS / Android / Web 基础适配 |
| **Sprint 5 总计** | **30** | | |

#### Sprint 5 Demo 检查清单

- [ ] 可生成评估报告
- [ ] Grafana 看板可查看 QPS/Latency/错误率
- [ ] 项目部署到服务器并可访问
- [ ] 在线 Demo 可用
- [ ] 技术博客发布

---

### Sprint 6：RAG 内核升级 + LlamaIndex 迁移

**时间**：第 13-14 周  
**目标**：在不破坏现有问答 API、SSE、引用展示和评估体系的前提下，将现有手写 RAG 链路收敛到 LlamaIndex 可扩展检索内核，优先提升检索质量、引用稳定性和后续工具化扩展能力。  
**交付物**：LlamaIndex 检索适配层 + Milvus/Embedding 接入 + 查询引擎 + 评估对比报告

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S6-1] 梳理现有 RAG 链路并定义 LlamaIndex 迁移边界 | 2 | S3, S4, S5-2 | 明确保留 Gateway/Flutter API，不重写上传、任务和 SSE；输出迁移风险清单 |
| [S6-2] 引入 LlamaIndex 依赖与配置开关 | 2 | S6-1 | 增加 feature flag：`RAG_ENGINE=legacy/llamaindex`，默认兼容 legacy |
| [S6-3] 实现 LlamaIndex Document/Node 元数据映射 | 3 | S3-1, S4-5 | 将 resource/chunk/page/timestamp/citation metadata 映射到 LlamaIndex Node |
| [S6-4] 接入 LlamaIndex Milvus VectorStore 与 Embedding 适配器 | 5 | S3-2, S3-3 | 复用现有 embedding provider；保持 Milvus collection 与 metadata filter 可控 |
| [S6-5] 实现 LlamaIndex Retriever/QueryEngine 封装 | 5 | S6-3, S6-4 | 支持 top_k、resource scope、跨文档查询、空结果降级 |
| [S6-6] 将 QA Service 接入可切换 RAG Engine | 5 | S6-5, S3-6 | 现有 SSE 事件格式、引用格式、错误格式保持兼容 |
| [S6-7] 增加 LlamaIndex RAG 评估对比脚本 | 3 | S5-1, S5-2, S6-6 | 对比 legacy 与 llamaindex 的 recall、faithfulness、citation accuracy |
| [S6-8] 更新 RAG 架构文档与调试 Runbook | 2 | S6-6 | 说明迁移边界、配置、回滚方式和常见故障 |
| **Sprint 6 总计** | **27** | | |

#### Sprint 6 Demo 检查清单

- [ ] `RAG_ENGINE=legacy` 与 `RAG_ENGINE=llamaindex` 均可通过同一问答接口使用
- [ ] Flutter 聊天页无需修改即可接收 LlamaIndex 答案和引用
- [ ] 引用仍可跳转到音频时间戳或 PDF 页码
- [ ] 评估报告能对比 legacy 与 LlamaIndex 两套检索效果
- [ ] 可通过配置一键回滚到 legacy RAG

---

### Sprint 7：MCP 能力接入底座

**时间**：第 15-16 周  
**目标**：为 MKC 增加可控的 MCP 工具接入能力，让 Agent 能通过白名单工具访问外部能力，同时保留权限、审计、超时、错误降级和前端可解释性。  
**交付物**：MCP Server/Tool Registry + 工具调用运行时 + Agent 工具节点 + 调用审计

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S7-1] 定义 MKC MCP 产品边界与权限模型 | 3 | S4-4, S5-6 | 明确先支持 server-side MCP client，不让浏览器直连外部 MCP；定义工具白名单 |
| [S7-2] 设计 MCP Server 与 Tool Registry 数据模型/API | 3 | S7-1 | Gateway 负责用户可见配置与权限；AI Service 负责执行前读取可用工具 |
| [S7-3] 实现 AI Service MCP Client 抽象与 mock provider | 5 | S7-2 | 支持 list tools、call tool、timeout、schema validation、错误归一化 |
| [S7-4] 实现工具调用审计与观测事件 | 3 | S5-3, S5-4, S7-3 | 记录 trace_id、conversation_id、tool_name、latency、success/failure，不记录敏感参数 |
| [S7-5] 将 MCP 工具接入 LangGraph Agent 工具节点 | 5 | S4-4, S7-3 | Agent 可在知识库不足时调用已授权工具；失败时降级为知识库回答 |
| [S7-6] Flutter 增加 MCP 工具配置与调用可见性 MVP | 5 | S7-2, S7-4 | 设置页展示已启用工具；聊天页展示“调用了哪些工具”的摘要 |
| [S7-7] 增加 MCP 安全测试与 Runbook | 3 | S7-3, S7-5 | 覆盖未授权工具、超时、注入参数、敏感字段脱敏、回滚开关 |
| **Sprint 7 总计** | **27** | | |

#### Sprint 7 Demo 检查清单

- [ ] 管理端或配置文件可注册一个 mock MCP server
- [ ] Agent 能列出并调用白名单 MCP 工具
- [ ] 未授权工具调用被拒绝且有明确错误
- [ ] 聊天回答能展示工具调用摘要
- [ ] 工具调用有 trace/metrics/audit 记录，敏感参数不落日志

---

### Sprint 8：Skill 系统与可组合工作流

**时间**：第 17-18 周  
**目标**：在 MCP 底座之上提供面向用户和开发者的 Skill 能力，让常见知识工作流可以被配置、复用、评估和逐步产品化。  
**交付物**：Skill Manifest + Skill Registry + 执行器 + 内置技能 + Flutter Skill 页面

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S8-1] 定义 Skill Manifest 与生命周期 | 3 | S7-1 | 约定 skill id、name、description、inputs、tools、permissions、prompts、version |
| [S8-2] 实现 Skill Registry 与加载机制 | 3 | S8-1 | 初期支持仓库内置 YAML/JSON manifest，后续再考虑用户上传 |
| [S8-3] 实现 Skill Executor 与参数校验 | 5 | S8-1, S7-3 | 将 skill 输入转为 Agent/Tool 调用计划；校验权限、参数 schema、超时 |
| [S8-4] 内置“资料总结”与“跨文档对比”两个技能 | 5 | S8-3, S6-6 | 复用 LlamaIndex RAG、引用和摘要能力，保证可演示价值 |
| [S8-5] 内置“学习卡片/复习题生成”技能 | 3 | S8-3, S6-6 | 从资源内容生成 flashcards 或 quiz，输出结构化 JSON 与 Markdown |
| [S8-6] Flutter 增加 Skill 入口与执行结果页 | 5 | S8-2, S8-4 | 资源详情和聊天页可启动技能；展示执行进度、结果、引用 |
| [S8-7] Skill 评估、审计与文档 | 3 | S5-2, S7-4, S8-4 | 每个内置技能至少有 golden cases；记录执行日志与失败原因 |
| **Sprint 8 总计** | **27** | | |

#### Sprint 8 Demo 检查清单

- [ ] 系统能加载内置 Skill Manifest
- [ ] 用户可从 Flutter 选择资源并运行“资料总结”
- [ ] 用户可运行“跨文档对比”并得到带引用的结果
- [ ] 用户可生成学习卡片或复习题
- [ ] Skill 调用可审计、可评估、可禁用

---

### Sprint 9：能力市场化与多工具协同增强

**时间**：第 19-20 周  
**目标**：将 MCP 与 Skill 从 MVP 升级为可持续扩展能力，重点补齐多工具规划、权限治理、用户体验和线上稳定性，为后续“个人知识工作台”形态做准备。  
**交付物**：Skill/MCP 管理体验 + 多工具计划器 + 权限提示 + 质量门禁

| 任务卡 | 故事点 | 依赖 | 说明 |
|---|---|---|---|
| [S9-1] Skill/MCP 管理页增强 | 5 | S7-6, S8-6 | 支持启用/禁用、查看权限、查看版本、查看最近调用 |
| [S9-2] Agent 多工具计划器与执行限制 | 5 | S7-5, S8-3 | 控制最大工具调用次数、循环检测、成本预算、人工确认点 |
| [S9-3] 用户级权限与敏感操作确认 | 5 | S7-1, S9-2 | 高风险工具调用前要求确认；权限变更写入审计 |
| [S9-4] Skill 结果结构化存储与历史复用 | 3 | S8-6 | 将技能输出存为资源派生结果，可重新打开、复制、继续追问 |
| [S9-5] 引入真实 MCP 示例工具 | 3 | S7-3 | 选择一个低风险工具，如网页抓取摘要或本地文件索引 mock，不接入高风险写操作 |
| [S9-6] 端到端质量门禁与回归套件 | 5 | S6-S8 | 覆盖 LlamaIndex、MCP、Skill 的主路径和降级路径 |
| **Sprint 9 总计** | **26** | | |

#### Sprint 9 Demo 检查清单

- [ ] 用户能管理 MCP 工具和 Skill 权限
- [ ] Agent 能完成一个多工具协同任务并展示调用计划
- [ ] 高风险操作有确认机制
- [ ] Skill 结果能持久化并继续追问
- [ ] 回归套件覆盖 RAG、MCP、Skill 三条主链路

---

## 四、任务卡模板

每个任务卡建议按以下格式创建（可直接复制到 GitHub Issues / Notion）：

```markdown
## [S1-1] 实现用户注册/登录 API

**所属史诗**：E1 用户认证
**故事点**：3
**优先级**：Must
**依赖**：S0-4 数据库 Schema
**目标 Sprint**：Sprint 1

### 描述
作为用户，我需要注册和登录系统，以便安全访问我的知识库。

### 验收标准（AC）
- [ ] POST /api/v1/auth/register 成功创建用户并返回 access_token 与 refresh_token
- [ ] POST /api/v1/auth/login 验证密码并返回 access_token 和 refresh_token
- [ ] POST /api/v1/auth/refresh 用有效 refresh_token 换取新 access_token
- [ ] POST /api/v1/auth/logout 删除 Redis Session，refresh_token 失效
- [ ] 密码使用 bcrypt 哈希存储，不存明文
- [ ] 邮箱唯一性校验，重复注册返回 409
- [ ] 单元测试覆盖率 80%+

### 技术要点
- Go + Gin + GORM
- JWT + Redis Session 混合鉴权
  - access_token：短期 JWT，网关无状态快速校验
  - refresh_token：随机字符串，存储于 Redis Session，支持吊销与多设备管理
- 输入校验与统一错误响应

### 阻塞风险
- 无

### 备注
- access_token 有效期 15 分钟
- refresh_token 有效期 7 天，以 Session 形式存储在 Redis，支持登出吊销与多设备管理
```

---

## 五、关键依赖路径

```
S0 基础设施
    │
    ├──→ S1 认证 + 上传 + 任务
    │        │
    │        ├──→ S2 MP3 转录 + PDF 解析
    │        │        │
    │        │        ├──→ S3 Embedding + RAG 问答
    │        │                 │
    │        │                 ├──→ S4 Agent + 溯源 + 抽取
    │        │                          │
    │        │                          └──→ S5 评估 + 可观测 + 上线
    │        │                                   │
    │        │                                   └──→ S6 LlamaIndex RAG 内核升级
    │        │                                             │
    │        │                                             └──→ S7 MCP 能力接入底座
    │        │                                                       │
    │        │                                                       └──→ S8 Skill 系统
    │        │                                                                 │
    │        │                                                                 └──→ S9 多工具协同增强
    │        │
    │        └──→ S5 部署环境准备
    │
    └──→ S5 监控基础设施
```

**核心依赖说明**：

- S3 必须在 S2 完成后开始，因为需要先有转录/解析后的文本才能做 Embedding。
- S4 必须在 S3 完成后开始，因为 Agent 工作流依赖基础 RAG 能力。
- S5 的部署和监控依赖前面所有 Sprint 的成果。
- S6 应优先于 MCP/Skill，因为 LlamaIndex 统一 RAG 内核后，后续工具和技能能复用稳定的检索、引用和评估能力。
- S7 应先于 S8，因为 Skill 需要调用工具、声明权限和复用工具审计能力。
- S9 放在 S8 之后，作为多工具协同、权限治理和体验完善阶段，避免 MCP/Skill MVP 阶段范围过大。

---

## 六、故事点总览

| Sprint | 主题 | 故事点 | 关键交付 |
|---|---|---|---|
| Sprint 0 | 基础设施 | 18 | 本地 K8s + CI + 三端骨架 |
| Sprint 1 | 认证上传 | 22 | 注册登录 + 文件上传 + 任务进度 |
| Sprint 2 | 内容处理 | 23 | MP3 转 SRT + PDF 解析 |
| Sprint 3 | RAG 问答 | 32 | Embedding + 向量检索 + SSE 流式问答 |
| Sprint 4 | 智能增强 | 32 | LangGraph Agent + 引用溯源 + 摘要标签 |
| Sprint 5 | 生产上线 | 30 | 评估 + 监控 + K8s 部署 + 博客 |
| Sprint 6 | RAG 内核升级 | 27 | LlamaIndex RAG + 评估对比 + 回滚开关 |
| Sprint 7 | MCP 能力底座 | 27 | MCP Registry + 工具调用 + 审计 |
| Sprint 8 | Skill 系统 | 27 | Skill Manifest + 内置技能 + 前端入口 |
| Sprint 9 | 多工具协同 | 26 | 权限治理 + 多工具计划器 + 回归门禁 |
| **总计** | | **262** | |

**说明**：单人项目建议每个 Sprint 承担 20-30 故事点。Sprint 3/4 工作量较大，如果感觉吃紧，可将部分任务延后到 Sprint 5 或砍掉可选功能。

---

## 七、风险管理

| 风险 | 发生阶段 | 影响 | 应对策略 |
|---|---|---|---|
| faster-whisper 本地运行慢 | S2 | 转录 1 小时音频超过预期 | 先用 `small` 模型跑通，上线前换 `large-v3`；或接入云端 ASR API |
| Milvus 本地资源占用高 | S3 | 电脑跑不起来 | Sprint 0 先用 Chroma，S3 再迁移到 Milvus |
| LLM API 费用超预期 | S3-S5 | 测试阶段消耗大量 token | 使用国产模型免费额度；控制并发；评估数据集先小规模 |
| Agent 工作流过于复杂 | S4 | 开发周期延长 | 先实现固定路由（if-else），再优化为动态意图识别 |
| Flutter 多端适配工作量大 | S5 | 上线延迟 | MVP 先保证 iOS/Android/Web，鸿蒙和桌面端后续扩展 |
| SSE 全链路调试困难 | S3 | 流式输出不稳定 | 分段测试：Python → curl → Go → Flutter |
| 引用溯源准确性差 | S4 | 用户点击引用跳转错误 | 分块时严格保留元数据；增加引用校验节点 |
| LlamaIndex 迁移破坏现有问答链路 | S6 | SSE、引用或评估回归 | 使用 `RAG_ENGINE` 双引擎开关，先并行对比，再切默认 |
| MCP 工具带来安全边界扩大 | S7-S9 | 未授权访问、敏感参数泄露、工具滥用 | 服务端白名单、schema 校验、超时、审计、敏感字段脱敏 |
| Skill 范围膨胀成插件市场 | S8-S9 | 排期失控、验收不清 | 先只做内置 manifest 和 2-3 个高频技能，不做用户上传第三方技能 |
| 多工具 Agent 循环或成本失控 | S9 | 延迟过高、费用不可控 | 设置最大调用次数、递归限制、预算、人工确认点 |

---

## 八、每周检查清单

### 每周五 15 分钟 Sprint 回顾

1. 本周完成了哪些任务卡？
2. 哪些卡延期？原因是什么？
3. 下周优先级最高的是什么？
4. 有没有需要调整 Sprint 范围的地方？
5. 技术上有什么阻塞需要寻求帮助？

### 每日站会三问

1. 昨天完成了什么？
2. 今天计划做什么？
3. 遇到什么阻塞？

### 每个 Sprint 结束 Demo 主题

| Sprint | Demo 主题 |
|---|---|
| S0 | `kubectl apply -f infra/k8s/` 启动所有服务，三端健康检查通过 |
| S1 | 注册 → 上传 MP3 → 看任务进度实时更新 |
| S2 | 查看生成的 SRT 和 PDF 结构化文本 |
| S3 | 向知识库提问，看到 SSE 流式回答 |
| S4 | 答案带引用，点击跳转到音频时间戳/PDF 页码 |
| S5 | 在线 Demo + Grafana 监控 + LLM-as-judge 评估报告 |
| S6 | 同一问答接口可切换 legacy/LlamaIndex RAG，并输出效果对比 |
| S7 | Agent 可安全调用白名单 MCP 工具，调用过程可观测可审计 |
| S8 | 用户可运行内置 Skill 完成总结、对比和学习卡片生成 |
| S9 | 多工具协同任务可执行、可确认、可回溯、可回归测试 |

---

## 九、总览：Sprint 交付地图

```
Week:  1-2   3-4   5-6   7-8   9-10  11-12
       ├─────┼─────┼─────┼─────┼─────┤
       │ S0  │ S1  │ S2  │ S3  │ S4  │ S5  │
       │     │     │     │     │     │     │
       │基建  │上传  │转录  │RAG  │Agent│上线  │
       │     │     │解析  │问答  │溯源 │     │
       └─────┴─────┴─────┴─────┴─────┘
```

```text
Week:  13-14 15-16 17-18 19-20
       ├─────┼─────┼─────┼─────┤
       │ S6  │ S7  │ S8  │ S9  │
       │RAG  │MCP  │Skill│协同  │
       │升级  │底座  │系统  │治理  │
       └─────┴─────┴─────┴─────┘
```

| Sprint | 主题 | 核心交付 | 简历可写点 |
|---|---|---|---|
| S0 | 基础设施 | 本地一键启动环境 | 项目工程化基础 |
| S1 | 认证上传 | 注册登录 + 文件上传 + 任务进度 | 端到端文件上传与异步任务 |
| S2 | 内容处理 | MP3 转 SRT + PDF 解析 | ASR、PDF 解析流水线 |
| S3 | RAG 问答 | 向知识库提问 + SSE 流式 | RAG、Embedding、向量检索 |
| S4 | 智能增强 | Agent、溯源、摘要标签 | LangGraph Agent、引用溯源 |
| S5 | 生产上线 | 评估、监控、部署、博客 | LLM-as-judge、可观测、DevOps |
| S6 | RAG 内核升级 | LlamaIndex 双引擎、检索评估对比 | LlamaIndex、RAG 迁移、可回滚架构 |
| S7 | MCP 能力底座 | MCP 工具注册、调用、审计 | MCP、Tool Calling、安全边界 |
| S8 | Skill 系统 | 可配置技能、内置工作流、前端入口 | Agent Skill、工作流产品化 |
| S9 | 多工具协同 | 权限治理、多工具计划器、回归门禁 | 多 Agent 工具编排、权限治理 |

---

## 十、Sprint 执行建议

### 10.1 Sprint 0 启动清单

- [ ] 创建 GitHub 仓库
- [ ] 创建 GitHub Project 看板
- [ ] 把本文档所有任务卡录入看板
- [ ] 配置本地开发环境（Docker、Go、Python、Flutter）
- [ ] 配置本地 K8s 开发环境（minikube / k3d / kind）
- [ ] 跑通第一个 `kubectl apply -f infra/k8s/`

### 10.2 代码提交规范

遵循 [TECH_S0-1_github_repo_init.md](./tech/TECH_S0-1_github_repo_init.md) 中的 Git 工作流约定：

```
<type>: <description>

[optional body]
```

类型：`feat`、`fix`、`refactor`、`docs`、`test`、`chore`、`perf`、`ci`

示例：

```
feat: 实现用户注册登录 API

- 添加 JWT 双 Token 机制
- 添加 bcrypt 密码哈希
- 添加注册登录单元测试
```

### 10.3 每个 Sprint 的范围控制原则

- **必须完成**：所有标记 Must 的故事
- **尽量完成**：Should 类故事
- **可选做**：Could 类故事，可延后
- **本周不做**：明确推迟到下个 Sprint

---

## 十一、附录：任务卡速查表

| 任务卡 | Sprint | 故事点 | 优先级 |
|---|---|---|---|
| S0-1 初始化 GitHub 仓库 | S0 | 1 | Must |
| S0-2 本地 K8s 环境 + manifests | S0 | 5 | Must |
| S0-3 GitHub Actions CI | S0 | 2 | Must |
| S0-4 数据库 Schema | S0 | 2 | Must |
| S0-5 API 接口文档 | S0 | 2 | Must |
| S0-6 Flutter 骨架 | S0 | 2 | Must |
| S0-7 Go Gateway 骨架 | S0 | 2 | Must |
| S0-8 Python AI Service 骨架 | S0 | 2 | Must |
| S1-1 注册/登录 API | S1 | 3 | Must |
| S1-2 Flutter 登录/注册页 | S1 | 2 | Must |
| S1-3 文件上传 API | S1 | 5 | Must |
| S1-4 Flutter 文件上传页 | S1 | 3 | Must |
| S1-5 任务状态 API | S1 | 3 | Must |
| S1-6 Flutter 任务中心 | S1 | 3 | Must |
| S1-7 任务进度 SSE | S1 | 3 | Must |
| S2-1 faster-whisper ASR | S2 | 5 | Must |
| S2-2 SRT 生成 | S2 | 2 | Must |
| S2-3 音频文本清洗 | S2 | 3 | Should |
| S2-4 PDF 文本提取 | S2 | 3 | Must |
| S2-5 PDF OCR | S2 | 2 | Could |
| S2-6 存储结果 | S2 | 2 | Must |
| S2-7 内容查看页 | S2 | 3 | Must |
| S2-8 异步任务重试 | S2 | 3 | Must |
| S3-1 文本分块 | S3 | 3 | Must |
| S3-2 Embedding | S3 | 3 | Must |
| S3-3 Milvus 集成 | S3 | 5 | Must |
| S3-4 向量检索 | S3 | 5 | Must |
| S3-5 LLM 接入 | S3 | 3 | Must |
| S3-6 SSE 问答 API | S3 | 5 | Must |
| S3-7 Flutter 对话页 | S3 | 5 | Must |
| S3-8 会话消息持久化 | S3 | 3 | Must |
| S4-1 摘要提取 | S4 | 3 | Should |
| S4-2 标签实体抽取 | S4 | 3 | Should |
| S4-3 资源卡片升级 | S4 | 2 | Should |
| S4-4 LangGraph Agent | S4 | 8 | Should |
| S4-5 引用溯源 | S4 | 5 | Should |
| S4-6 引用跳转 | S4 | 3 | Should |
| S4-7 混合检索重排 | S4 | 5 | Should |
| S4-8 Web Search | S4 | 3 | Could |
| S5-1 评估数据集 | S5 | 3 | Could |
| S5-2 LLM-as-judge | S5 | 5 | Could |
| S5-3 OpenTelemetry | S5 | 3 | Could |
| S5-4 Prometheus/Grafana | S5 | 3 | Could |
| S5-5 LangSmith/Langfuse | S5 | 2 | Could |
| S5-6 错误降级 | S5 | 3 | Should |
| S5-7 README 文档 | S5 | 2 | Should |
| S5-8 K8s 部署上线 | S5 | 5 | Should |
| S5-9 技术博客 | S5 | 2 | Should |
| S5-10 多端适配 | S5 | 2 | Should |
| S6-1 RAG 链路梳理与迁移边界 | S6 | 2 | Must |
| S6-2 LlamaIndex 依赖与配置开关 | S6 | 2 | Must |
| S6-3 Document/Node 元数据映射 | S6 | 3 | Must |
| S6-4 LlamaIndex Milvus/Embedding 适配 | S6 | 5 | Must |
| S6-5 Retriever/QueryEngine 封装 | S6 | 5 | Must |
| S6-6 QA Service 双引擎接入 | S6 | 5 | Must |
| S6-7 RAG 评估对比脚本 | S6 | 3 | Should |
| S6-8 RAG 架构文档与 Runbook | S6 | 2 | Should |
| S7-1 MCP 边界与权限模型 | S7 | 3 | Must |
| S7-2 MCP Registry 数据模型/API | S7 | 3 | Must |
| S7-3 AI Service MCP Client 抽象 | S7 | 5 | Must |
| S7-4 工具调用审计与观测 | S7 | 3 | Must |
| S7-5 MCP 接入 Agent 工具节点 | S7 | 5 | Must |
| S7-6 Flutter MCP 配置与调用可见性 | S7 | 5 | Should |
| S7-7 MCP 安全测试与 Runbook | S7 | 3 | Must |
| S8-1 Skill Manifest 与生命周期 | S8 | 3 | Must |
| S8-2 Skill Registry 与加载机制 | S8 | 3 | Must |
| S8-3 Skill Executor 与参数校验 | S8 | 5 | Must |
| S8-4 内置资料总结/跨文档对比技能 | S8 | 5 | Must |
| S8-5 内置学习卡片/复习题技能 | S8 | 3 | Should |
| S8-6 Flutter Skill 入口与结果页 | S8 | 5 | Should |
| S8-7 Skill 评估、审计与文档 | S8 | 3 | Must |
| S9-1 Skill/MCP 管理页增强 | S9 | 5 | Should |
| S9-2 Agent 多工具计划器与执行限制 | S9 | 5 | Must |
| S9-3 用户级权限与敏感操作确认 | S9 | 5 | Must |
| S9-4 Skill 结果结构化存储与历史复用 | S9 | 3 | Should |
| S9-5 真实 MCP 示例工具 | S9 | 3 | Should |
| S9-6 端到端质量门禁与回归套件 | S9 | 5 | Must |

---

*排卡完成。下一步建议：将任务卡录入 GitHub Project 或 Notion 看板，然后从 Sprint 0 开始执行。*
