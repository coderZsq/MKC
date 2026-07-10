# PRD：[S3-6] 实现 SSE 问答 API

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S1-7_task_progress_push.md](./PRD_S1-7_task_progress_push.md)、[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)、[PRD_S3-5_glm4_kimi_llm.md](./PRD_S3-5_glm4_kimi_llm.md)、[PRD_S3-7_flutter_chat_page.md](./PRD_S3-7_flutter_chat_page.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-6 |
| **任务名称** | 实现 SSE 问答 API |
| **所属史诗** | E7 AI 对话 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S1-7 SSE 任务进度推送、S3-5 LLM 接入 |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为用户，当我向知识库提问时，我希望能够实时看到 AI 生成的答案，而不是等待完整响应。本任务在 Gateway 提供 `GET /api/v1/conversations/{id}/events` 或 `POST /api/v1/conversations/{id}/ask` SSE 问答端点，Gateway 调用 AI Service 的检索与 LLM 流式生成能力，将增量内容通过 SSE 转发给 Flutter/Web 客户端。同时需要与 S3-8 的会话消息持久化联动，保存用户问题和最终答案。

---

## 验收标准（AC）

- [ ] **AC-1** Gateway 提供 SSE 问答端点，支持 JWT 认证，Web 端通过 `?token=` 查询参数传 token
- [ ] **AC-2** 用户提问时，Gateway 将问题、资源范围、会话历史传递给 AI Service
- [ ] **AC-3** AI Service 完成向量检索、上下文组装，并调用 LLM 流式生成答案
- [ ] **AC-4** Gateway 将 LLM 增量内容以 SSE 事件流式返回给客户端，事件类型包括 `chunk`、`citation`、`done`、`error`
- [ ] **AC-5** 每个 `chunk` 事件包含当前增量文本与完整消息 ID
- [ ] **AC-6** `citation` 事件包含来源信息：资源 ID、页码或时间戳、相似度分数
- [ ] **AC-7** 问答完成后，Gateway 将完整答案写入 S3-8 会话消息表
- [ ] **AC-8** SSE 连接异常断开时，客户端可重连并继续获取后续内容（或降级为轮询）
- [ ] **AC-9** 单元/集成测试覆盖率 80%+，包含 Gateway 与 AI Service 流式链路测试

---

## 推荐目录结构

### Gateway

```
gateway/
├── internal/
│   ├── handler/
│   │   └── qa_sse_handler.go
│   ├── service/
│   │   ├── qa_service.go
│   │   └── ai_client.go           # 调用 AI Service 流式接口
│   └── router/
│       └── router.go
```

### AI Service

```
ai-service/
├── app/
│   ├── api/
│   │   └── qa.py                  # 问答 SSE 接口
│   ├── services/
│   │   ├── qa_service.py          # 问答编排：检索 + LLM
│   │   └── sse_formatter.py       # SSE 事件格式化
```

---

## 核心依赖

### Gateway

| 依赖 | 版本 | 用途 |
|---|---|---|
| gin-gonic/gin | v1.10.x | HTTP 路由与流式响应 |
| 标准库 `net/http` | - | SSE 流式转发 |

### AI Service

| 依赖 | 版本 | 用途 |
|---|---|---|
| Flask/FastAPI | 2.3+ / 0.110+ | SSE 接口 |
| zhipuai / openai | - | LLM 流式生成 |

---

## 技术要点

### SSE 事件格式

```text
event: chunk
data: {"message_id":"...","conversation_id":"...","delta":"本次","index":0}

event: chunk
data: {"message_id":"...","conversation_id":"...","delta":"会议","index":1}

event: citation
data: {"message_id":"...","resource_id":"...","score":0.89,"metadata":{"page":3}}

event: done
data: {"message_id":"...","finish_reason":"stop"}

event: error
data: {"message_id":"...","error_code":"LLM_TIMEOUT","message":"生成超时"}

```

### 问答流程

1. 客户端请求 SSE 问答端点，携带问题与资源范围
2. Gateway 校验 JWT 与资源权限
3. 从 S3-8 获取会话历史消息，组装成 messages
4. 调用 AI Service 的问答接口（流式）
5. AI Service：检索 → 上下文组装 → LLM 流式生成
6. Gateway 将 LLM 增量与引用信息以 SSE 转发
7. 流式结束后，Gateway 保存完整答案到消息表

### 错误处理与降级策略

- LLM 超时：返回 error 事件并保存部分答案
- 检索无结果：Prompt 中提示无上下文，继续生成通用回答
- AI Service 不可用：返回 503，Gateway 提示用户稍后重试
- 客户端断开：保留已生成内容，不重试；用户再次提问可继续

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| SSE 全链路调试困难 | 流式输出不稳定 | 分段测试：Python → curl → Go → Flutter |
| 网关连接池耗尽 | 高并发问答失败 | 限制单用户同时连接数，配置超时 |
| 消息持久化与流式顺序冲突 | 消息丢失或重复 | 由 Gateway 统一落库，AI Service 只负责生成 |

---

## Web 端适配

- Web 端浏览器 `EventSource` 不支持自定义请求头，JWT 通过 `?token=` 查询参数传递
- Gateway 为 SSE 问答端点配置 CORS，允许 Flutter Web 域名访问
- Web 端优先使用 `dart:html` 原生 `EventSource`，移动端/桌面端使用 dio 流式读取
- 断线后执行自动重连与 5 秒轮询降级，最多重试 5 次

---

## 备注

- S3-6 的 SSE 协议需要与 S1-7 的 SSE 任务进度协议保持一致，便于客户端统一解析
- 建议将 AI Service 的问答接口设计为独立端点，便于 S4 Agent 工作流直接复用
- 引用信息（citation）格式需要与 S3-7 对话页面的渲染组件对齐
