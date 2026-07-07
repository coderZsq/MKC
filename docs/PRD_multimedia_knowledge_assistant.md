# PRD：多媒体 AI 知识库助手（Multimedia Knowledge Companion）

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 目标：基于 Flutter + Go + Python 构建一个生产级别的个人 AI 应用项目，用于转行 AI 应用工程师。

---

## 一、文档信息

### 1.1 术语表

| 术语 | 说明 |
|---|---|
| ASR | 自动语音识别（Automatic Speech Recognition） |
| SRT | SubRip Subtitle，带时间轴的字幕文件格式 |
| RAG | 检索增强生成（Retrieval-Augmented Generation） |
| Agent | 基于 LLM 的自主决策与工具调用工作流 |
| Embedding | 文本向量化表示 |
| Chunk | 知识库中的最小检索单元 |
| BFF | Backend For Frontend，面向客户端的后端聚合层 |
| SSE | Server-Sent Events，服务器推送流式协议 |
| LLM-as-judge | 使用 LLM 自动评估生成结果质量 |

### 1.2 参考简历

本 PRD 所有技术选型与架构设计均围绕简历中的实战经验展开：

- **AI / LLM 应用**：LangGraph · LangChain · LlamaIndex · RAG · Prompt Engineering · SSE 流式 · LLM-as-judge
- **模型与向量**：text-embedding-v3 · Milvus · 智谱 GLM · 月之暗面 Kimi · 通义千问
- **后端与服务化**：Python · Java · Go · Docker · Kubernetes · Jenkins
- **跨端交付**：Flutter · iOS · Android · HarmonyOS · Method Channel / JSBridge

---

## 二、项目概述

### 2.1 项目背景

个人在日常学习、工作和研究中积累大量音频（播客、会议录音、课程、访谈）和 PDF（论文、报告、书籍、手册）资料。这些资料信息密度高，但存在以下问题：

1. **查找困难**：想回顾某个知识点时，需要重新听音频或翻 PDF。
2. **理解成本高**：长音频和长文档需要大量时间消化。
3. **知识孤立**：音频和文档之间无法联动检索。
4. **无法对话**：无法像和人交流一样向资料提问。

本项目旨在通过 AI 技术，将 MP3/PDF 自动转录、提炼、结构化，构建统一的个人知识库，实现自然语言检索、对话问答、精确溯源。

### 2.2 项目定位

**产品名称**：多媒体 AI 知识库助手（Multimedia Knowledge Companion，简称 MKC）

**一句话定位**：把你的音频和文档变成可检索、可对话、可溯源的智能知识库。

**核心能力**：

- MP3 → SRT 字幕 + 清洗文本 + 章节摘要
- PDF → 结构化文本 + 目录层级 + 页码映射
- 统一向量知识库，支持语义检索 + 关键词检索
- 基于 LangGraph 的 Agent 多轮对话问答
- 答案精确溯源到音频时间戳或 PDF 页码

### 2.3 项目目标

1. **转行目标**：完整展示 AI 应用工程师所需的端到端能力。
2. **技术目标**：构建可运行、可演示、可扩展的生产级系统。
3. **学习目标**：深入实践 ASR、RAG、Agent、向量库、流式交互、可观测性。
4. **品牌目标**：作为 GitHub 开源项目 + 技术博客素材，增强简历说服力。

---

## 三、目标用户与核心场景

### 3.1 目标用户

- 需要处理大量会议录音的职场人士
- 需要整理播客/课程内容的终身学习者
- 需要管理论文/报告的研究人员
- 需要构建个人知识库的工程师

### 3.2 核心场景

#### 场景 1：播客学习

> 小王每周听 3 期技术播客，每期 1 小时。他把 MP3 上传到 MKC，系统自动生成 SRT 和 10 分钟摘要。他想了解"RAG 的评估方法"，直接提问，系统给出答案并标注"来自第 23 分 15 秒"。

#### 场景 2：会议回顾

> 项目经理上传了一场 2 小时的线上会议录音。系统自动区分发言人，生成会议纪要、待办事项。团队成员可以提问"会上关于排期的结论是什么？"，系统给出准确回答。

#### 场景 3：论文研读

> 研究生上传了 5 篇 PDF 论文。系统提取每篇摘要、方法、结论，并自动生成标签。他可以提问"这几篇论文在向量检索方法上有什么异同？"，系统跨文档给出对比分析。

#### 场景 4：知识沉淀

> 工程师长期使用 MKC 积累技术资料，形成个人知识库。遇到问题时直接提问，系统基于历史资料给出带来源引用的答案。

---

## 四、功能需求

### 4.1 功能架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter 客户端                            │
│  ├─ 首页/知识库列表                                          │
│  ├─ 文件上传（MP3/PDF）                                       │
│  ├─ 任务中心（转录/解析进度）                                  │
│  ├─ 内容查看（SRT 字幕 / PDF 文本 / 章节摘要）                  │
│  ├─ AI 对话（SSE 流式渲染 / Markdown / 引用卡片）              │
│  └─ 个人中心（设置 / API Key / 用量统计）                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS / SSE / WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                    Go API Gateway                            │
│  ├─ 用户认证（JWT / 注册 / 登录）                              │
│  ├─ 文件上传（分片/合并/MinIO 存储）                           │
│  ├─ 任务调度（异步任务状态管理）                               │
│  ├─ 会话管理（多轮对话 / 历史消息）                            │
│  ├─ SSE 代理（AI 服务流式响应透传）                            │
│  ├─ 限流熔断（Token Bucket / 超时控制）                        │
│  └─ 埋点与日志（OpenTelemetry Trace）                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ gRPC / HTTP
┌─────────────────────▼───────────────────────────────────────┐
│                  Python AI Service                           │
│  ├─ ASR Worker：MP3 → SRT + 文本                              │
│  ├─ PDF Parser：PDF → 结构化文本                               │
│  ├─ Information Extractor：摘要 / 标签 / 实体 / 章节           │
│  ├─ Embedding Pipeline：分块 → Embedding → Milvus             │
│  ├─ RAG Engine：混合检索 / 重排序 / 上下文组装                  │
│  ├─ Agent Workflow：LangGraph 多节点编排                       │
│  ├─ LLM Service：智谱 GLM / Kimi / 通义千问                     │
│  └─ Evaluation：LLM-as-judge 质量评估                         │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 客户端功能（Flutter）

#### 4.2.1 知识库管理

| 功能 | 需求描述 |
|---|---|
| 文件上传 | 支持从手机/电脑选择 MP3 和 PDF 文件；大文件支持分片上传 |
| 上传队列 | 显示上传进度、暂停/恢复、失败重试 |
| 资源卡片 | 每个资源展示文件名、类型图标、处理状态、摘要、标签 |
| 资源筛选 | 按类型（音频/文档）、标签、时间筛选 |
| 资源搜索 | 在资源标题/摘要中快速搜索 |
| 资源删除 | 删除资源及其关联的向量数据、SRT、文本 |

#### 4.2.2 任务中心

| 功能 | 需求描述 |
|---|---|
| 任务列表 | 展示所有异步任务（上传/转录/解析/向量化） |
| 实时进度 | 通过 SSE/WebSocket 接收任务进度更新 |
| 任务状态 | pending / processing / success / failed / retrying |
| 失败重试 | 支持单个任务重试 |

#### 4.2.3 内容查看

| 功能 | 需求描述 |
|---|---|
| SRT 播放器 | 音频播放时高亮当前字幕，支持点击字幕跳转 |
| 文本视图 | 展示清洗后的转录文本，按章节折叠 |
| PDF 视图 | 展示解析后的结构化文本，显示页码 |
| 摘要视图 | 展示全文摘要、章节摘要、关键实体、标签 |
| 引用跳转 | 从问答引用卡片跳转到对应时间戳或页码 |

#### 4.2.4 AI 对话

| 功能 | 需求描述 |
|---|---|
| 会话列表 | 多会话管理，自动生成会话标题 |
| 消息渲染 | 支持 Markdown、代码块、引用卡片 |
| 流式输出 | SSE 流式接收 AI 回复，逐字渲染 |
| 引用溯源 | 每条引用展示来源文件名、页码/时间戳、原文片段 |
| 消息操作 | 复制、重新生成、点赞/点踩反馈 |
| 上下文管理 | 多轮对话上下文，支持清除上下文 |

#### 4.2.5 个人中心

| 功能 | 需求描述 |
|---|---|
| 用户设置 | 模型选择、温度参数、最大 token |
| API Key 管理 | 用户可配置自己的 LLM API Key（可选） |
| 用量统计 | 上传文件数、转录时长、问答次数 |
| 深色模式 | 支持系统/浅色/深色切换 |

### 4.3 网关功能（Go）

#### 4.3.1 认证与授权

| 功能 | 需求描述 |
|---|---|
| 用户注册 | 邮箱 + 密码注册 |
| 用户登录 | JWT + Session 混合登录：签发短期 access_token（JWT）+ 长期 refresh_token（存 Redis Session） |
| 权限校验 | 中间件校验 JWT access_token；关键操作可二次校验 Session 状态 |
| Token 刷新 | 用 refresh_token 换取新 access_token，服务端校验 Redis Session 有效性 |
| 登出与会话管理 | 登出删除 Redis Session，支持多设备会话查看与吊销 |
| API Key 认证 | 为第三方调用提供 API Key（可选） |

#### 4.3.2 文件与任务管理

| 功能 | 需求描述 |
|---|---|
| 文件上传 | 接收分片上传，合并后存入 MinIO |
| 文件下载 | 提供 SRT / 原始文件下载 |
| 任务创建 | 文件上传成功后创建异步处理任务 |
| 任务查询 | 查询任务状态、进度、结果 |
| 任务重试 | 失败任务支持重试，带指数退避 |

#### 4.3.3 会话与消息

| 功能 | 需求描述 |
|---|---|
| 会话 CRUD | 创建、查询、更新、删除会话 |
| 历史消息 | 分页拉取会话历史消息 |
| SSE 问答 | 建立 SSE 连接，转发 Python 服务流式响应 |

#### 4.3.4 网关治理

| 功能 | 需求描述 |
|---|---|
| 限流 | 按用户维度 Token Bucket 限流 |
| 熔断 | AI 服务异常时快速失败并返回友好提示 |
| 超时控制 | 上传、问答接口分别设置超时 |
| 日志追踪 | 每个请求注入 Trace ID，全链路透传 |

### 4.4 AI 服务功能（Python）

#### 4.4.1 ASR 转录模块

| 功能 | 需求描述 |
|---|---|
| 音频预处理 | ffmpeg 统一格式、采样率、分片 |
| 语音转录 | 基于 faster-whisper 生成带时间戳的文本 |
| SRT 生成 | 按标准 SRT 格式输出字幕文件 |
| 文本清洗 | 去除语气词、重复、口误，LLM 二次润色 |
| 说话人分离 | 可选 pyannote.audio 区分发言人 |
| 时间戳对齐 | 每个句子保留 start_time / end_time |

#### 4.4.2 PDF 解析模块

| 功能 | 需求描述 |
|---|---|
| 文本提取 | pymupdf / pdfplumber 提取文本 |
| 目录解析 | 识别 PDF 目录结构，构建章节层级 |
| 页码映射 | 每个段落保留 page_number |
| OCR 识别 | paddleocr 处理扫描件 |
| 表格提取 | 可选提取表格为 Markdown 表格 |
| 元数据提取 | 标题、作者、关键词 |

#### 4.4.3 信息抽取模块

| 功能 | 需求描述 |
|---|---|
| 全文摘要 | 生成 200 字内全文摘要 |
| 章节摘要 | 为每个章节生成小标题和摘要 |
| 关键词/标签 | 自动提取 5-10 个主题标签 |
| 命名实体 | 提取人名、机构、技术术语、产品名 |
| 待办提取 | 会议场景中自动提取 Action Items |
| 问答对生成 | 自动生成 FAQ 用于评估 |

#### 4.4.4 向量知识库模块

| 功能 | 需求描述 |
|---|---|
| 文本分块 | 按语义/章节/长度多策略分块 |
| Embedding | text-embedding-v3 / BGE-M3 生成向量 |
| 向量存储 | Milvus 存储向量 + 元数据 |
| 混合检索 | 向量检索 + BM25 关键词检索 |
| 重排序 | Cross-Encoder 对候选片段重排 |
| 元数据过滤 | 按 source_type / source_id / 标签过滤 |

#### 4.4.5 RAG 问答模块

| 功能 | 需求描述 |
|---|---|
| 查询理解 | 改写、扩展、意图识别 |
| 检索组装 | 多路召回 Top-K 片段 |
| 上下文构建 | 按优先级组装片段，控制 token 长度 |
| 答案生成 | LLM 基于上下文生成带引用答案 |
| 引用格式化 | 答案中嵌入 [^1] [^2] 引用标记 |
| 流式输出 | 通过 SSE 逐 token 返回答案 |

#### 4.4.6 Agent 工作流模块

基于 **LangGraph** 设计多节点状态机：

```
          ┌─────────────┐
          │  用户输入    │
          └──────┬──────┘
                 ▼
          ┌─────────────┐
          │ 意图识别节点 │
          │  classify   │
          └──────┬──────┘
                 ▼
    ┌────────────────────────┐
    │  路由：summarize / qa  │
    │  / search / compare    │
    └───────┬────────────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ 总结节点 │   │ 检索节点 │   │ 搜索节点 │   │ 对比节点 │
│ summarize│   │ retrieve│   │ web_search│  │ compare │
└────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
     │             │             │             │
     └─────────────┴──────┬──────┴─────────────┘
                          ▼
                   ┌─────────────┐
                   │  生成节点    │
                   │   generate  │
                   └──────┬──────┘
                          ▼
                   ┌─────────────┐
                   │  引用校验节点 │
                   │   verify    │
                   └──────┬──────┘
                          ▼
                   ┌─────────────┐
                   │  返回答案    │
                   └─────────────┘
```

各节点说明：

| 节点 | 职责 |
|---|---|
| 意图识别 | 判断用户是要总结、问答、搜索还是跨文档对比 |
| 检索节点 | 从 Milvus 召回相关片段 |
| 搜索节点 | 调用 Web Search 工具补充外部信息（可选） |
| 总结节点 | 对单文档/多文档进行摘要 |
| 对比节点 | 对比多个文档的相同主题 |
| 生成节点 | 基于上下文生成答案 |
| 引用校验 | 检查生成内容是否有引用支撑 |

#### 4.4.7 评估模块

基于 **LLM-as-judge** 构建评估流水线：

| 指标 | 评估方式 |
|---|---|
| 上下文召回率 | 评估检索出的片段是否包含答案所需信息 |
| 忠实度 | 评估生成答案是否忠于检索内容，无幻觉 |
| 回答相关性 | 评估答案是否直接回应用户问题 |
| 引用准确性 | 评估引用的时间戳/页码是否正确 |
| 答案完整性 | 评估答案是否覆盖问题的多个方面 |

评估结果用于：
- 自动发现 Badcase
- 优化 Prompt 和分块策略
- A/B 测试不同 Embedding 和 LLM

---

## 五、非功能需求

### 5.1 性能需求

| 指标 | 目标 |
|---|---|
| 音频转录 | 1 小时音频在 10 分钟内完成（本地 GPU/付费 API） |
| PDF 解析 | 100 页 PDF 在 30 秒内完成 |
| 问答首 token | < 2 秒 |
| 流式延迟 | 平均每个 token < 200ms |
| 检索延迟 | Top-K 检索 < 500ms |
| 并发 | 单实例支持 50 并发问答 |

### 5.2 可用性需求

| 指标 | 目标 |
|---|---|
| 系统可用性 | 99.5%（个人项目目标） |
| 数据持久化 | 用户文件、会话、向量数据持久化存储 |
| 故障恢复 | 服务重启后任务状态可恢复 |
| 离线降级 | 已加载内容支持离线查看，AI 问答需联网 |

### 5.3 安全需求

| 需求 | 说明 |
|---|---|
| 认证鉴权 | 所有接口需 JWT access_token 认证，关键操作二次校验 Redis Session |
| 输入校验 | 文件类型、大小、内容校验 |
| 文件隔离 | 用户文件按 user_id 隔离存储 |
| API Key 安全 | 不明文存储用户 LLM API Key，加密保存 |
| 错误脱敏 | 错误信息不暴露内部堆栈 |

### 5.4 可扩展性需求

| 需求 | 说明 |
|---|---|
| 模型可插拔 | LLM、Embedding、ASR 模型可配置切换 |
| 存储可扩展 | 向量库从 Chroma 平滑迁移到 Milvus |
| 任务队列可扩展 | 可水平扩展 Worker 处理转录任务 |
| 多端可扩展 | Flutter 一套代码覆盖 iOS / Android / macOS / Web |

### 5.5 可观测性需求

| 维度 | 工具/方案 |
|---|---|
| 链路追踪 | OpenTelemetry + Jaeger |
| 指标监控 | Prometheus + Grafana |
| 日志聚合 | Loki 或结构化日志文件 |
| LLM 观测 | LangSmith / Langfuse |
| 业务埋点 | 问答次数、转录时长、检索命中率 |

---

## 六、技术架构

### 6.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          客户端层                                   │
│   Flutter (iOS / Android / macOS / Web / HarmonyOS 潜力)            │
│   Clean Architecture + Riverpod StateNotifier                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS / SSE
┌───────────────────────────────▼─────────────────────────────────────┐
│                          网关层                                     │
│   Go + Gin + GORM + Redis + MinIO                              │
│   JWT + Session 认证 / 限流 / 文件上传 / 任务管理 / 会话管理 / SSE 代理          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ gRPC / HTTP
┌───────────────────────────────▼─────────────────────────────────────┐
│                         AI 服务层                                   │
│   Python + Flask + LangGraph + LlamaIndex + Celery                │
│   ASR / PDF 解析 / 信息抽取 / Embedding / RAG / Agent / 评估         │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   ┌─────────┐            ┌─────────┐            ┌───────────┐
   │ Milvus  │            │  MySQL   │            │  MinIO    │
   │ 向量库  │            │ 业务库   │            │ 对象存储   │
   └─────────┘            └─────────┘            └───────────┘
```

### 6.2 客户端架构（Flutter）

采用 **Clean Architecture**，与简历中沃尔沃项目保持一致：

```
lib/
├── main.dart
├── app.dart
├── core/
│   ├── constants/          # 常量
│   ├── errors/             # 异常定义
│   ├── network/            # Dio + SSE Client
│   ├── storage/            # Hive 本地缓存
│   ├── theme/              # 主题配置
│   └── utils/              # 工具函数
├── data/
│   ├── datasources/        # 远程/本地数据源
│   ├── models/             # DTO 模型
│   └── repositories/       # Repository 实现
├── domain/
│   ├── entities/           # 业务实体
│   ├── repositories/       # Repository 接口
│   └── usecases/           # UseCase
├── presentation/
│   ├── providers/          # Riverpod StateNotifier
│   ├── pages/              # 页面
│   ├── widgets/            # 组件
│   └── state/              # UI 状态
└── router/                 # 路由配置
```

状态管理：
- 使用 **Riverpod StateNotifier** 管理页面状态
- 定义统一的 `StatePageData<T>`：`initial / loading / success / failure / empty`

### 6.3 网关架构（Go）

```
gateway/
├── cmd/
│   └── server/             # 入口
├── internal/
│   ├── config/             # 配置管理
│   ├── handler/            # HTTP Handler
│   ├── middleware/         # JWT / 限流 / Trace
│   ├── model/              # 数据模型
│   ├── repository/         # 数据访问
│   ├── service/            # 业务逻辑
│   └── client/             # Python AI Service 客户端
├── pkg/
│   ├── logger/             # 日志
│   ├── errors/             # 错误码
│   └── utils/              # 工具
└── scripts/                # 脚本
```

**Go 网关技术选型**

- **Web 框架**：Gin（高性能、中间件生态成熟、与 GORM/Redis 集成方便）
- **数据库访问**：GORM + MySQL（驱动 `gorm.io/driver/mysql`，推荐 MySQL 8.0）
- **缓存 / Session**：go-redis
- **SSE 代理**： Gin 使用 `c.Stream()` 将 Python AI 服务的流式响应透传给 Flutter
- **对象存储**：MinIO 客户端

### 6.4 AI 服务架构（Python）

```
ai-service/
├── app/
│   ├── api/                # Flask 蓝图路由
│   ├── core/               # 配置/日志/异常
│   ├── workers/            # Celery 异步任务
│   │   ├── asr_worker.py
│   │   ├── pdf_worker.py
│   │   └── embedding_worker.py
│   ├── services/
│   │   ├── asr/
│   │   ├── pdf/
│   │   ├── extraction/
│   │   ├── embedding/
│   │   ├── retrieval/
│   │   ├── agent/
│   │   └── evaluation/
│   ├── graph/              # LangGraph 工作流
│   ├── models/             # Pydantic 模型
│   └── infrastructure/     # Milvus / MinIO / Redis 客户端
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evaluation/
├── notebooks/              # 实验笔记本
└── scripts/                # 工具脚本
```

**Python 服务技术选型**

- **Web 框架**：Flask（成熟、生态丰富、与 Celery 集成简单）
- **SSE 流式**：`flask.stream_with_context` + `Response(mimetype='text/event-stream')`，生产环境配合 Gunicorn + gevent/eventlet worker 处理长连接
- **任务队列**：Celery + Redis broker
- **数据校验**：Pydantic / Marshmallow
- **LangGraph / LlamaIndex**：编排 Agent 工作流与 RAG 管道

---

## 七、数据模型设计

### 7.1 MySQL 业务表

#### 用户表（users）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| email | VARCHAR | 邮箱，唯一 |
| password_hash | VARCHAR | 密码哈希 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### 资源表（resources）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| user_id | UUID | 用户 ID |
| name | VARCHAR | 文件名 |
| type | ENUM | audio / pdf |
| size | BIGINT | 文件大小 |
| mime_type | VARCHAR | MIME 类型 |
| storage_key | VARCHAR | MinIO 对象 key |
| status | ENUM | pending / processing / success / failed |
| duration | INT | 音频时长（秒） |
| page_count | INT | PDF 页数 |
| summary | TEXT | 全文摘要 |
| tags | JSON | 标签列表 |
| metadata | JSON | 元数据（作者、标题等） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### 任务表（tasks）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| user_id | UUID | 用户 ID |
| resource_id | UUID | 资源 ID |
| type | ENUM | asr / pdf_parse / embedding / extract |
| status | ENUM | pending / processing / success / failed / retrying |
| progress | INT | 进度 0-100 |
| result | JSON | 任务结果 |
| error | TEXT | 错误信息 |
| retry_count | INT | 重试次数 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### 会话表（conversations）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| user_id | UUID | 用户 ID |
| title | VARCHAR | 会话标题 |
| resource_ids | JSON | 关联资源 ID 列表 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### 消息表（messages）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| conversation_id | UUID | 会话 ID |
| role | ENUM | user / assistant / system |
| content | TEXT | 消息内容 |
| citations | JSON | 引用列表 |
| tokens_used | INT | token 用量 |
| latency_ms | INT | 响应延迟 |
| created_at | TIMESTAMP | 创建时间 |

### 7.2 向量库集合（Milvus）

集合名：`knowledge_chunks`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | VARCHAR | 主键 |
| user_id | VARCHAR | 用户 ID |
| resource_id | VARCHAR | 资源 ID |
| source_type | VARCHAR | audio / pdf |
| chunk_type | VARCHAR | summary / section / transcript / paragraph |
| content | VARCHAR | 文本内容 |
| embedding | FLOAT_VECTOR | 向量，维度 1024 / 768 |
| page_number | INT | PDF 页码 |
| start_time | FLOAT | 音频开始时间（秒） |
| end_time | FLOAT | 音频结束时间（秒） |
| section_title | VARCHAR | 章节标题 |
| tags | VARCHAR[] | 标签 |
| created_at | INT64 | 创建时间戳 |

索引：`IVF_FLAT` 或 `HNSW`

---

## 八、API 接口设计

### 8.1 认证接口

#### POST /api/v1/auth/register

```json
// Request
{
  "email": "user@example.com",
  "password": "secure_password"
}

// Response
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "access_token": "jwt",
    "refresh_token": "session_token",
    "expires_in": 900,
    "token_type": "Bearer"
  }
}
```

#### POST /api/v1/auth/login

```json
// Request
{
  "email": "user@example.com",
  "password": "secure_password"
}

// Response
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "access_token": "jwt",
    "refresh_token": "session_token",
    "expires_in": 900,
    "token_type": "Bearer"
  }
}
```

#### POST /api/v1/auth/refresh

```json
// Request
{
  "refresh_token": "session_token"
}

// Response
{
  "success": true,
  "data": {
    "access_token": "jwt",
    "refresh_token": "session_token",
    "expires_in": 900,
    "token_type": "Bearer"
  }
}
```

#### POST /api/v1/auth/logout

```json
// Request
{
  "refresh_token": "session_token"
}

// Response
{
  "success": true,
  "data": null
}
```

### 8.2 文件上传接口

#### POST /api/v1/resources/upload

支持 multipart/form-data 或分片上传。

```json
// Response
{
  "success": true,
  "data": {
    "resource_id": "uuid",
    "status": "processing",
    "task_id": "uuid"
  }
}
```

### 8.3 资源管理接口

#### GET /api/v1/resources

```json
// Response
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "meeting.mp3",
        "type": "audio",
        "status": "success",
        "duration": 3600,
        "summary": "本次会议讨论了...",
        "tags": ["会议", "产品"]
      }
    ],
    "total": 10,
    "page": 1,
    "limit": 20
  }
}
```

#### GET /api/v1/resources/:id

#### DELETE /api/v1/resources/:id

### 8.4 任务接口

#### GET /api/v1/tasks

#### GET /api/v1/tasks/:id

#### POST /api/v1/tasks/:id/retry

### 8.5 内容查看接口

#### GET /api/v1/resources/:id/srt

返回 SRT 字幕内容。

#### GET /api/v1/resources/:id/text

返回结构化文本（按章节）。

### 8.6 会话接口

#### POST /api/v1/conversations

```json
// Request
{
  "title": "关于 RAG 的讨论",
  "resource_ids": ["uuid1", "uuid2"]
}
```

#### GET /api/v1/conversations

#### GET /api/v1/conversations/:id/messages

### 8.7 问答接口（SSE）

#### POST /api/v1/conversations/:id/chat

请求头：`Accept: text/event-stream`

```json
// Request
{
  "message": "RAG 的评估方法有哪些？",
  "model": "glm-4",
  "temperature": 0.7
}
```

SSE 事件流：

```
event: message
data: {"type": "delta", "content": "RAG"}

event: message
data: {"type": "delta", "content": " 的评估方法"}

event: message
data: {"type": "citation", "citations": [{"id": 1, "source": "meeting.mp3", "start_time": 1395, "content": "..."}]}

event: message
data: {"type": "done"}
```

---

## 九、关键流程设计

### 9.1 MP3 处理流程

```
用户上传 MP3
    │
    ▼
Flutter 分片上传 → Go Gateway 合并 → MinIO
    │
    ▼
Go Gateway 创建 ASR Task → Celery Worker
    │
    ▼
ASR Worker:
  1. ffmpeg 格式检查与转换
  2. 音频分片（30s/段）
  3. faster-whisper 转录
  4. 合并时间戳
  5. 生成 SRT
  6. LLM 清洗语气词与重复
  7. 说话人分离（可选）
    │
    ▼
Extraction Worker:
  1. 生成全文摘要
  2. 章节分段与小标题
  3. 提取标签与实体
    │
    ▼
Embedding Worker:
  1. 按章节/句子分块
  2. text-embedding-v3 生成向量
  3. 写入 Milvus（含时间戳元数据）
    │
    ▼
更新 Resource/Task 状态
    │
    ▼
SSE/WebSocket 推送进度到 Flutter
```

### 9.2 PDF 处理流程

```
用户上传 PDF
    │
    ▼
Flutter 上传 → Go Gateway → MinIO
    │
    ▼
Go Gateway 创建 PDF Parse Task → Celery Worker
    │
    ▼
PDF Worker:
  1. pymupdf 提取文本
  2. 识别目录与章节层级
  3. OCR 扫描件（可选）
  4. 提取表格
    │
    ▼
Extraction Worker:
  1. 生成全文摘要
  2. 章节摘要
  3. 标签/实体/关键词
    │
    ▼
Embedding Worker:
  1. 按章节/段落分块
  2. 保留 page_number
  3. 写入 Milvus
    │
    ▼
更新 Resource/Task 状态
```

### 9.3 问答流程

```
用户输入问题
    │
    ▼
Flutter → Go Gateway → Python AI Service
    │
    ▼
LangGraph Agent:
  1. 意图识别（qa / summarize / search / compare）
  2. 路由到对应节点
  3. 检索节点：Milvus 向量检索 + BM25 召回 + 重排序
  4. 组装上下文（含 source_type / page / time）
  5. LLM 生成带引用答案
  6. 引用校验节点
    │
    ▼
SSE 流式返回到 Flutter
    │
    ▼
Flutter 渲染 Markdown + 引用卡片
    │
    ▼
用户点击引用 → 跳转 SRT 时间戳 / PDF 页码
```

---

## 十、生产级保障

### 10.1 可观测性

| 层级 | 方案 | 内容 |
|---|---|---|
| 客户端 | Firebase / 自建埋点 | 页面停留、功能点击、崩溃上报 |
| 网关 | OpenTelemetry + Prometheus | QPS、Latency、错误率、限流触发次数 |
| AI 服务 | LangSmith / Langfuse | LLM 调用、Agent 节点执行、Prompt 版本 |
| 向量库 | Milvus Metrics | 查询延迟、召回率 |
| 日志 | 结构化 JSON 日志 + Trace ID | 全链路排查 |

### 10.2 CI/CD

```yaml
# GitHub Actions 示例
name: CI/CD
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Python tests
        run: cd ai-service && pytest --cov=app
      - name: Run Go tests
        run: cd gateway && go test ./...
      - name: Run Flutter analyze
        run: cd client && flutter analyze
  build:
    needs: test
    steps:
      - name: Build Docker images
        run: |
          docker build -t mkc-gateway:${{ github.sha }} gateway/
          docker build -t mkc-ai-service:${{ github.sha }} ai-service/
          docker build -t mkc-client:${{ github.sha }} client/
      - name: Push to registry
        run: |
          docker push mkc-gateway:${{ github.sha }}
          docker push mkc-ai-service:${{ github.sha }}
          docker push mkc-client:${{ github.sha }}
      - name: Deploy to K8s
        run: |
          kubectl set image deployment/gateway gateway=mkc-gateway:${{ github.sha }}
          kubectl set image deployment/ai-service ai-service=mkc-ai-service:${{ github.sha }}
          kubectl set image deployment/client client=mkc-client:${{ github.sha }}
```

### 10.3 部署架构

本地开发：minikube / kind / k3d 本地 K8s 集群

生产部署：Kubernetes（云厂商托管集群或自管集群）

**基础设施组件（云原生依赖）**

```yaml
- nginx-ingress-controller   # 七层入口：TLS 终止、域名路由、限流基础层
- cert-manager               # 自动签发并续期 Let's Encrypt 证书
- mysql                 # 业务数据：用户、任务、会话、资源元信息
- redis                      # Session 存储、缓存、限流计数、任务队列 broker
- milvus                     # 向量检索
- minio                      # 对象存储
- jaeger                     # 分布式追踪
- prometheus                 # 指标采集
- grafana                    # 监控大盘
```

**核心应用工作负载**

```yaml
- gateway-deployment         # Go 网关
- ai-service-deployment      # Python AI API
- worker-deployment          # Celery Worker
- client-deployment          # Flutter Web（可选）
```

**K8s 资源组织**

```yaml
infra/k8s/
├── base/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── gateway/
│   ├── ai-service/
│   ├── worker/
│   ├── mysql/
│   ├── redis/
│   ├── milvus/
│   ├── minio/
│   ├── ingress/
│   └── monitoring/
├── overlays/
│   ├── local/               # 本地 minikube/k3d 覆盖层
│   └── production/          # 生产覆盖层
└── kustomization.yaml
```

### 10.4 安全与兜底

| 场景 | 方案 |
|---|---|
| 大文件上传 | 限制 500MB，分片上传，超时 30 分钟 |
| ASR 失败 | 自动重试 3 次，失败后用户可手动重试 |
| LLM 超时 | 10 秒无首 token 返回友好提示 |
| 敏感内容 | 输入过滤，避免注入 Prompt |
| Token 刷新 | SSE 连接断开时自动刷新 Token 重连 |
| 离线场景 | 已下载内容本地缓存，AI 问答提示网络异常 |

---

## 十一、测试与评估策略

### 11.1 测试覆盖

| 类型 | 工具 | 目标 |
|---|---|---|
| 单元测试 | pytest / go test / flutter_test | 核心函数 80%+ 覆盖 |
| 集成测试 | pytest + Testcontainers | AI 服务端到端 |
| 接口测试 | Postman / httpx | Gateway API |
| E2E 测试 | Flutter Integration Test | 上传 → 转录 → 问答 |

### 11.2 评估数据集

构建 50-100 条评估样本，覆盖：

- 音频问答（需要时间戳溯源）
- PDF 问答（需要页码溯源）
- 跨文档对比问答
- 总结类问题
- 实体/待办提取

### 11.3 评估指标

| 指标 | 目标 |
|---|---|
| 上下文召回率 | > 85% |
| 忠实度 | > 80% |
| 回答相关性 | > 85% |
| 引用准确率 | > 90% |

---

## 十二、里程碑与交付物

### Phase 1：基础闭环（3-4 周）

**目标**：实现 MP3/PDF 上传、处理、基础问答。

| 交付物 | 说明 |
|---|---|
| Flutter 上传页 + 资源列表 | UI 框架、状态管理、API 对接 |
| Go 网关认证 + 文件上传 | JWT + Redis Session、MinIO、任务创建 |
| Python ASR Worker | faster-whisper 生成 SRT + 文本 |
| Python PDF Worker | pymupdf 文本提取 |
| 基础 RAG | Chroma + text-embedding-v3 + GLM-4 |
| Kubernetes manifests | 本地/生产环境一键部署所有服务 |

### Phase 2：智能化 + 生产化（3 周）

| 交付物 | 说明 |
|---|---|
| LangGraph Agent | 意图识别 + 多节点工作流 |
| 信息抽取 | 摘要、标签、实体、章节 |
| 混合检索 + 重排序 | 向量 + BM25 + Cross-Encoder |
| 引用溯源 | 时间戳/页码精确跳转 |
| Milvus 替换 Chroma | 生产级向量库 |
| SSE 流式问答 | 全链路流式 |

### Phase 3：评估 + 可观测 + 上线（2-3 周）

| 交付物 | 说明 |
|---|---|
| LLM-as-judge | 自动评估流水线 |
| OpenTelemetry + Prometheus | 可观测体系 |
| GitHub Actions CI/CD | 自动化测试、构建、镜像推送 |
| K8s manifests | 生产部署配置 |
| 在线 Demo + 技术博客 | 简历与 GitHub 展示 |

---

## 十三、简历表达建议

在简历中可这样描述本项目：

> **多媒体 AI 知识库助手 | 个人开源项目**
>
> - 独立设计并实现支持 MP3/PDF 多端上传的 AI 知识库系统，覆盖音频 ASR 转录、PDF 解析、智能信息抽取、RAG 检索问答、Agent 工作流编排全链路。
> - 基于 faster-whisper 实现音频到 SRT + 清洗文本的转录流水线，结合 LLM 完成章节化、摘要、标签与实体抽取；PDF 解析保留目录层级与页码映射。
> - 使用 LangGraph 编排意图识别、检索、重排序、生成、引用校验多节点 Agent 工作流，答案支持精确到音频时间戳与 PDF 页码的引用溯源。
> - Flutter 端基于 Clean Architecture + Riverpod StateNotifier 实现跨端上传、SSE 流式问答、任务进度推送、引用跳转与离线缓存。
> - Go 网关负责 JWT 鉴权、限流熔断、文件分片上传、任务调度与 SSE 代理；Python AI 服务承担 ASR、RAG、Embedding、LLM 调用与评估。
> - 引入 LLM-as-judge 评估回答质量与检索效果，接入 OpenTelemetry、Prometheus、Grafana 构建可观测体系，GitHub Actions + Kubernetes manifests 实现持续交付。

---

## 十四、风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| ASR 转录耗时长 | 用户体验差 | 异步任务 + 进度推送；支持 GPU/云端 API 切换 |
| 长文本分块质量差 | 检索效果差 | 按章节分块 + 摘要块 + 重叠窗口 |
| LLM 幻觉 | 答案不可信 | 严格基于检索上下文 + 引用校验 + LLM-as-judge |
| 个人项目成本 | GPU/云 API 费用 | 优先使用本地 faster-whisper + 国产 LLM 免费额度 |
| 多端适配工作量大 | 交付延迟 | MVP 先聚焦 iOS/Android + Web，鸿蒙后续扩展 |

---

## 十五、附录

### 15.1 推荐开源库

| 用途 | 库 |
|---|---|
| ASR | faster-whisper, whisper.cpp |
| PDF 解析 | pymupdf, pdfplumber, marker |
| OCR | paddleocr, tesseract |
| Embedding | text-embedding-v3, BGE-M3 |
| 向量库 | Chroma, Milvus |
| LLM 框架 | LangChain, LlamaIndex, LangGraph |
| 评估 | ragas, trulens |
| Go Web | Gin |
| Flutter 状态 | Riverpod, flutter_riverpod |

### 15.2 推荐模型

| 用途 | 模型/服务 |
|---|---|
| ASR | faster-whisper-large-v3 |
| Embedding | text-embedding-v3 |
| LLM | 智谱 GLM-4 / 月之暗面 Kimi / 通义千问 |
| 重排序 | bge-reranker-large |
| 说话人分离 | pyannote/speaker-diarization |

---

*PRD 完成。下一步建议：基于本 PRD 输出系统架构图、数据库 Schema SQL、API 详细文档，然后进入 Phase 1 开发。*
