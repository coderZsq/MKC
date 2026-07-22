# 技术文档：[S6-1] 梳理现有 RAG 链路并定义 LlamaIndex 迁移边界

> 版本：v1.1
> 日期：2026-07-22
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-1_rag_migration_boundary.md](../prd/PRD_S6-1_rag_migration_boundary.md)

---

## 1. 文档目标

定义 S6 LlamaIndex 迁移的系统边界、保留契约、可替换模块、风险清单和回滚策略，为后续
S6-2 到 S6-8 提供统一技术基线。

S6-1 不改变线上行为，只冻结现有 RAG 链路的输入、输出、引用、评估和回滚边界。后续任务
如发现实现与本文不一致，应优先保护 Gateway、Flutter、SSE 和 citation 外部契约，并把差异
记录到对应任务卡。

---

## 2. 技术栈

- Python 3.11+
- Flask / Celery
- Milvus / pymilvus
- LlamaIndex 0.10+ / 0.11+
- pydantic 2.x
- pytest 8.x
- Go 1.22+ / Gin / GORM
- Flutter Web / Riverpod / SSE client

---

## 3. 现有 RAG 链路

### 3.1 调用路径

当前问答链路从 Flutter Web 发起，经过 Gateway 持久化与 SSE 转发，再进入 AI Service
完成检索、Prompt 拼装、LLM 流式生成和引用构造。

```text
Flutter ChatPage
  -> ChatRepositoryImpl.sendQuestion()
  -> ChatSseClient.ask()
  -> POST /api/v1/conversations/{id}/ask
  -> gateway/internal/handler/qa_sse_handler.go
  -> gateway/internal/service/qa_service.go
  -> AIClient.StreamQA()
  -> POST /ai/v1/qa/stream
  -> ai-service/app/api/qa.py
  -> ai-service/app/services/qa_service.py
  -> RetrievalService.retrieve()
  -> EmbeddingService.embed_query()
  -> VectorStore.search()
  -> MilvusStore.search()
  -> PromptBuilder.build()
  -> LLMClient.stream_complete()
  -> CitationService.build_citations()
  -> SSE chunk/reasoning/citation/done/error
```

### 3.2 关键模块

| 模块 | 当前文件 | 职责 | S6 边界 |
|---|---|---|---|
| Flutter Chat | `client/lib/presentation/providers/chat_provider.dart` | 消费 SSE，拼接消息、reasoning 和 citation | 保持不变 |
| Flutter SSE parser | `client/lib/data/datasources/remote/chat_event_parser.dart` | 解析 `event:` 和 JSON `data:` | 保持不变 |
| Gateway SSE handler | `gateway/internal/handler/qa_sse_handler.go` | 暴露 `/conversations/:id/ask` 并透传 SSE | 保持不变 |
| Gateway QA service | `gateway/internal/service/qa_service.go` | 校验会话、保存消息、解析资源范围、保存回答 | 保持不变 |
| AI QA API | `ai-service/app/api/qa.py` | 暴露 `/ai/v1/qa/stream` 内部 SSE 接口 | 保持不变 |
| AI QA service | `ai-service/app/services/qa_service.py` | 编排 retrieval、LLM stream、citation、fallback | 只改注入点 |
| Retrieval service | `ai-service/app/services/retrieval/retrieval_service.py` | embedding、向量搜索、过滤、压缩、Prompt 拼装 | 可替换 |
| Vector store | `ai-service/app/vector_store/vector_store.py` | 定义 `search/query/upsert/delete` 协议 | 保持协议 |
| Milvus store | `ai-service/app/vector_store/milvus_store.py` | Milvus schema、filter 表达式、score 归一化 | 适配复用 |
| Citation service | `ai-service/app/services/citation_service.py` | 从 answer marker 和 chunk metadata 构造 citation | 保持输出 |
| Eval pipeline | `ai-service/eval/pipeline.py` | 跑数据集、answer provider、judge、report | S6-7 复用并扩展 |

### 3.3 核心数据模型

`QARequest` 位于 `ai-service/app/models/qa.py`，AI Service 问答入口必须继续接受以下字段：

- `question`
- `conversation_id`
- `message_id`
- `user_id`
- `resource_ids`
- `history`
- `top_k`
- `score_threshold`
- `max_context_tokens`
- `temperature`
- `max_tokens`

`RetrievalRequest` 和 `RetrievalResult` 位于 `ai-service/app/models/retrieval.py`。S6 的 legacy 与
LlamaIndex 两套引擎必须共享同一内部契约：

- 输入：`question`、`user_id`、`resource_ids`、`top_k`、`score_threshold`、`max_context_tokens`
- 输出：`chunks`、`prompt`、`context_token_count`
- chunk 字段：`chunk_id`、`resource_id`、`text`、`score`、`metadata`

`VectorRecord` 和 `VectorSearchResult` 位于 `ai-service/app/models/vector_record.py`。LlamaIndex
Node 映射必须保留：

- `id` -> `chunk_id`
- `resource_id`
- `user_id`
- `text`
- `metadata`
- `score`
- `created_at`

### 3.4 Milvus schema 与 filter

现有 Milvus collection 由 `MilvusStore._build_schema()` 管理，字段如下：

| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | VARCHAR primary key | chunk/vector 主键 |
| `vector` | FLOAT_VECTOR | embedding 向量 |
| `resource_id` | VARCHAR | 资源隔离与 citation 跳转 |
| `user_id` | VARCHAR | 用户隔离 |
| `text` | VARCHAR | 检索文本 |
| `metadata` | JSON | 页码、时间戳、资源类型等引用元数据 |
| `created_at` | INT64 | 写入时间 |

当前 filter 由 `_search_filter()` 生成，必须同时约束 `user_id` 与 `resource_ids`。LlamaIndex
adapter 不得绕过此约束；若官方 Milvus VectorStore 无法表达同等 filter，S6-4 应包装现有
`VectorStore.search()` 作为 fallback。

### 3.5 Citation schema

SSE `citation` 事件由 `CitationService` 和 `CitationFormatter` 生成，Flutter 端按
`CitationData`/`Citation` 消费。以下字段视为稳定外部契约：

| 字段 | 说明 |
|---|---|
| `message_id` | 目标 assistant message |
| `index` | 当前回答中的 citation 序号 |
| `original_index` | marker 重排前的序号，可为空 |
| `chunk_id` | 检索 chunk ID |
| `resource_id` | 引用资源 ID，必填 |
| `resource_type` | `audio` 或 `pdf` |
| `page` | PDF 页码，可为空 |
| `timestamp_start` | 音频起始秒，可为空 |
| `timestamp_end` | 音频结束秒，可为空 |
| `score` | 检索相似度 |
| `snippet` | 引用片段 |

AI Service 可在内部增加 metadata，但不得删除上述字段或改变字段语义。

### 3.6 SSE 事件契约

本任务不新增运行时接口，只冻结既有契约。

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/qa/stream` | Internal API Key | QA SSE 内部接口，S6 必须兼容 |
| POST | `/api/v1/conversations/{id}/ask` | Bearer JWT | Gateway 对外问答接口，不因 S6 改动 |
| CLI | `python -m eval.pipeline` | 本地环境变量 | S5 评估流水线，S6-7 复用 |

SSE 事件类型保持：`chunk`、`reasoning`、`citation`、`done`、`error`。

`chunk` data 必须包含：

- `message_id`
- `conversation_id`
- `delta`
- `index`

`reasoning` data 必须包含：

- `message_id`
- `conversation_id`
- `delta`
- `index`

`done` data 必须包含：

- `message_id`
- `finish_reason`
- `citation_count`
- `degraded`

`error` data 必须包含：

- `message_id`
- `conversation_id`
- `error_code`
- `code`
- `message`
- `trace_id`
- `retryable`
- `details`

---

## 4. 保留契约

S6 不修改以下模块和契约：

- Gateway 对外 API：`POST /api/v1/conversations/{id}/ask`
- Gateway auth 行为：Bearer JWT 校验、会话归属校验、资源范围解析
- Gateway SSE 转发格式：`event: <type>\ndata: <json>\n\n`
- Gateway 会话持久化：user message、assistant message、reasoning、citations 保存逻辑
- AI Service 内部 API：`POST /ai/v1/qa/stream`
- Flutter Chat 页面、Provider、Repository 与 SSE parser
- SSE event type 和字段语义
- citation schema 与 citation jump 所需字段
- Milvus 已有 collection schema
- S5 eval dataset 与 report 基本格式

后续任务可新增内部接口或 adapter，但不得要求 Flutter 或 Gateway 感知
`legacy`/`llamaindex` 两种引擎差异。

---

## 5. LlamaIndex 迁移范围

### 5.1 可替换范围

S6 只在 AI Service 内部引入可切换 RAG Engine：

- retrieval engine：从现有 `RetrievalService` 抽象出 `RagEngine` 协议
- node mapping：实现 `VectorRecord`/`VectorSearchResult`/`RetrievalChunk` 与 LlamaIndex Node 映射
- embedding adapter：复用现有 `EmbeddingService.embed_query()`
- Milvus adapter：复用现有 collection、filter 和 score 语义
- query engine：封装 LlamaIndex retriever，输出 `RetrievalResult`
- eval compare：在 S6-7 对比 legacy 与 llamaindex 的 recall、faithfulness、citation accuracy

### 5.2 不迁移范围

- 不重写上传、解析、chunking、embedding 写入链路
- 不重建 Milvus collection
- 不修改 Gateway response envelope
- 不修改 Flutter Chat UI 或 citation navigation
- 不改变 LLM streaming 的最终回答生成职责
- 不把 LlamaIndex 对象直接暴露给 Gateway 或 Flutter

### 5.3 目标抽象

```python
class RagEngine(Protocol):
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Return chunks and prompt using the stable MKC retrieval contract."""


def build_rag_engine(config: RagEngineConfig) -> RagEngine:
    if config.engine == "legacy":
        return LegacyRagEngine(...)
    if config.engine == "llamaindex":
        return LlamaIndexRagEngine(...)
    raise RagEngineConfigError("unsupported RAG_ENGINE")
```

`QAService` 后续只依赖 `RagEngine`，不直接依赖 LlamaIndex。`LegacyRagEngine` 包装当前
`RetrievalService`，用于默认行为和快速回滚。

---

## 6. 配置与双引擎策略

S6 统一以 `RAG_ENGINE` 作为切换入口：

```yaml
rag:
  engine: "${RAG_ENGINE:-legacy}"
  allowed_engines:
    - legacy
    - llamaindex
```

策略：

1. S6-2 引入配置和依赖，默认值必须是 `legacy`。
2. S6-3 到 S6-5 完成 LlamaIndex 内部 adapter，但不改变默认线上行为。
3. S6-6 将 QA Service 接入 factory，单实例只能选择一个当前引擎。
4. S6-7 使用同一数据集分别运行 `legacy` 与 `llamaindex`，输出对比报告。
5. S6-8 文档化 runbook、观测指标、回滚步骤。

默认放量顺序：

- 本地 smoke：`RAG_ENGINE=llamaindex`
- 测试环境：单实例或单 deployment 运行 llamaindex
- 灰度环境：固定测试账号或固定流量入口
- 生产默认切换：必须等待 S6-7 指标达标和 S6-8 runbook 完成

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 非法 RAG_ENGINE | N/A | RAG_ENGINE_INVALID | RAG 引擎配置不合法 |
| LlamaIndex 依赖不可用 | 503 | RAG_ENGINE_UNAVAILABLE | RAG 引擎不可用 |
| metadata 映射失败 | 500 | RAG_METADATA_INVALID | 检索元数据不合法 |
| 检索后端不可用 | 503 | RETRIEVAL_UNAVAILABLE | 检索不可用 |
| 向量存储不可用 | 503 | VECTOR_STORE_UNAVAILABLE | 向量存储不可用 |
| 越权检索结果 | 403 | RETRIEVAL_FORBIDDEN | 无权访问资源 |

SSE error event 不输出 Python stack trace、本地路径、依赖版本细节或任何密钥内容。

---

## 8. 回滚策略

快速回滚条件：

- citation 缺失率或 citation jump 失败率明显上升
- metadata filter 出现越权或漏过滤
- Milvus adapter 与旧 collection schema 不兼容
- LlamaIndex 依赖导致启动失败或镜像体积超出部署限制
- S6-7 指标低于 legacy 基线，尤其是 recall 与 citation accuracy
- QA SSE `chunk/done/error` 事件异常，Flutter Chat 无法稳定收尾

回滚步骤：

1. 设置 `RAG_ENGINE=legacy`。
2. 重启 AI Service 实例。
3. 使用同一个 Web Chat 页面发起 smoke question，确认收到 `chunk`、可选 `citation`、`done`。
4. 运行 S5/S6 smoke eval，确认 legacy 指标恢复到基线。

回滚不需要修改 Gateway、Flutter、Milvus schema 或历史会话数据。

---

## 9. 迁移风险清单

| 风险 | 影响 | 触发点 | 缓解 |
|---|---|---|---|
| 引用丢失 | Flutter 不显示来源，citation jump 失效 | Node metadata 未保留 `chunk_id/page/timestamp` | S6-3 双向映射测试覆盖 citation 字段 |
| metadata filter 漏约束 | 用户越权看到其他资源内容 | LlamaIndex filter 表达式与现有 Milvus filter 不等价 | S6-4 强制 `user_id` 与 `resource_ids` 共同过滤 |
| Milvus schema 不兼容 | llamaindex 引擎无法查询旧索引 | 官方 VectorStore 要求不同字段或 collection 参数 | 保留旧 schema，必要时包装现有 `VectorStore.search()` |
| score 语义漂移 | top_k、threshold、排序异常 | Milvus distance 与 LlamaIndex score 归一化不同 | adapter 统一输出 0 到 1 的 `score` |
| context token 失控 | Prompt 超长或成本升高 | QueryEngine 直接拼接大量 Node | S6-5 继续执行 `max_context_tokens` 压缩 |
| 评估波动 | 无法判断是否可切默认 | judge 或数据集不稳定 | S6-7 固定 smoke 数据集并输出 delta |
| 依赖体积增大 | 镜像启动慢或部署失败 | 引入完整 LlamaIndex 插件集 | S6-2 只引 core，S6-4 再加必要插件 |
| SSE 事件漂移 | Web Chat 无法结束流或无法重试 | 新引擎错误未映射到标准 event | S6-6 对 `chunk/citation/done/error` 做兼容测试 |
| 空结果体验倒退 | 用户收到不可解释空答案 | Retriever 空结果直接进入 LLM | S6-5/S6-6 明确空结果降级文案 |

---

## 10. Web 端适配要点

Flutter Web 无需新增配置。验收时需通过同一 Web Chat 页面分别验证 legacy 与 LlamaIndex 模式：

- 问答能流式显示 `chunk`
- reasoning 可选显示，不应阻塞回答
- citation card 能显示页码或时间戳
- citation click 能跳转到 content view
- `done` 后 loading 状态收尾
- `error.retryable=true` 时保留重试入口

---

## 11. 测试策略

- 静态测试：检查本文覆盖 QAService、RetrievalService、VectorStore、Citation、Eval。
- 契约测试：S6-6 覆盖 `chunk/reasoning/citation/done/error` 字段兼容。
- 权限测试：S6-4/S6-5 验证检索结果必须匹配 `user_id` 与 `resource_ids`。
- 引用测试：S6-3/S6-5 验证 page、timestamp、chunk_id、score 不丢失。
- 回归测试：legacy 模式运行现有 QA、Gateway、Flutter Chat 测试。
- 评估测试：S6-7 对比 legacy 与 llamaindex 指标。
- 文档检查：markdownlint。

测试用例映射：

| 用例 ID | 覆盖方式 |
|---|---|
| MKC-TC-S6-1-001 | 第 3 章列出现状模块、模型、调用路径和 Eval |
| MKC-TC-S6-1-002 | 第 4 章冻结 Gateway、Flutter、SSE、citation |
| MKC-TC-S6-1-003 | 第 5 章定义 retrieval engine、node mapping、query engine、eval 范围 |
| MKC-TC-S6-1-004 | 第 8 章定义 `RAG_ENGINE=legacy` 回滚 |
| MKC-TC-S6-1-005 | 本文仅使用占位配置，无真实密钥 |
| MKC-TC-S6-1-006 | 第 9 章覆盖引用、filter、Milvus、评估、依赖风险 |
| MKC-TC-S6-1-007 | markdownlint 静态检查 |

---

## 12. 检查清单

- [x] RAG 现状链路已梳理
- [x] 保留契约已明确
- [x] 迁移范围已明确
- [x] 回滚策略已明确
- [x] 风险清单已明确
