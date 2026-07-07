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
    │        │
    │        └──→ S5 部署环境准备
    │
    └──→ S5 监控基础设施
```

**核心依赖说明**：

- S3 必须在 S2 完成后开始，因为需要先有转录/解析后的文本才能做 Embedding。
- S4 必须在 S3 完成后开始，因为 Agent 工作流依赖基础 RAG 能力。
- S5 的部署和监控依赖前面所有 Sprint 的成果。

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
| **总计** | | **155** | |

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

| Sprint | 主题 | 核心交付 | 简历可写点 |
|---|---|---|---|
| S0 | 基础设施 | 本地一键启动环境 | 项目工程化基础 |
| S1 | 认证上传 | 注册登录 + 文件上传 + 任务进度 | 端到端文件上传与异步任务 |
| S2 | 内容处理 | MP3 转 SRT + PDF 解析 | ASR、PDF 解析流水线 |
| S3 | RAG 问答 | 向知识库提问 + SSE 流式 | RAG、Embedding、向量检索 |
| S4 | 智能增强 | Agent、溯源、摘要标签 | LangGraph Agent、引用溯源 |
| S5 | 生产上线 | 评估、监控、部署、博客 | LLM-as-judge、可观测、DevOps |

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

遵循 [common/git-workflow.md](./.claude/rules/common/git-workflow.md) 中的约定：

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

---

*排卡完成。下一步建议：将任务卡录入 GitHub Project 或 Notion 看板，然后从 Sprint 0 开始执行。*
