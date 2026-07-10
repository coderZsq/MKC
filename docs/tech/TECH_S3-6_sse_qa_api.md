# 技术文档：[S3-6] 实现 SSE 问答 API

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：后端/AI 工程师
> 关联 PRD：[../prd/PRD_S3-6_sse_qa_api.md](../prd/PRD_S3-6_sse_qa_api.md)

---

## 1. 文档目标

定义 Gateway 与 AI Service 之间 SSE 问答链路的完整技术实现：接口契约、流式转发、错误处理、会话消息持久化联动与测试策略。

---

## 2. 技术栈

### Gateway

- Go 1.22+
- Gin 1.10.x
- 标准库 `net/http`

### AI Service

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+

---

## 3. 接口契约

### Gateway 端点

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/conversations/{id}/ask` | Bearer JWT | 提问并建立 SSE 流 |

### AI Service 端点

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/qa/stream` | Internal API Key | 流式问答生成 |

### Gateway 请求示例

```json
POST /api/v1/conversations/{id}/ask
Authorization: Bearer <token>
{
  "question": "本次会议的议题是什么？"
}
```

### 响应头

```text
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

---

## 4. 配置

### Gateway

```yaml
ai_service:
  base_url: "${AI_SERVICE_URL}"
  internal_key: "${AI_SERVICE_INTERNAL_KEY}"

qa:
  timeout: 120
  max_sse_connections: 10
```

### AI Service

```yaml
qa:
  default_top_k: 5
  score_threshold: 0.7
  max_context_tokens: 4096
```

---

## 5. 模块设计

### Gateway

```go
type QASSEHandler struct {
    aiClient   *AIServiceClient
    convRepo   *ConversationRepository
    msgRepo    *MessageRepository
}

func (h *QASSEHandler) Ask(c *gin.Context) {
    // 1. 校验会话权限
    // 2. 保存用户消息
    // 3. 调用 AI Service 流式接口
    // 4. 转发 SSE 事件
    // 5. 保存完整答案
}
```

### AI Service

```python
class QAService:
    async def stream_answer(self, request: QARequest):
        # 1. 检索上下文
        # 2. 组装 messages
        # 3. 流式调用 LLM
        # 4. 格式化 SSE
```

---

## 6. 关键代码实现

### 6.1 Gateway SSE 转发（Go 伪代码）

```go
func (h *QASSEHandler) Ask(c *gin.Context) {
    c.Header("Content-Type", "text/event-stream; charset=utf-8")
    c.Header("Cache-Control", "no-cache")
    c.Header("Connection", "keep-alive")
    c.Status(http.StatusOK)
    flusher := c.Writer.(http.Flusher)

    stream, err := h.aiClient.StreamQA(ctx, request)
    if err != nil {
        fmt.Fprintf(c.Writer, "event: error\ndata: %s\n\n", err)
        flusher.Flush()
        return
    }

    var fullAnswer strings.Builder
    for event := range stream {
        fmt.Fprint(c.Writer, event.Raw)
        flusher.Flush()
        if event.Type == "chunk" {
            fullAnswer.WriteString(event.Delta)
        }
        if event.Type == "done" || event.Type == "error" {
            break
        }
    }

    h.msgRepo.SaveAssistantMessage(ctx, conversationID, fullAnswer.String())
}
```

### 6.2 AI Service 问答编排（Python 伪代码）

```python
async def stream_answer(self, request: QARequest):
    retrieval_result = await self._retrieval_service.retrieve(
        RetrievalRequest(question=request.question, ...)
    )
    messages = self._build_messages(request.history, retrieval_result.prompt)
    stream = self._llm_client.stream_complete(LLMRequest(messages=messages))
    async for chunk in stream:
        yield SseEvent(type="chunk", data={"delta": chunk.delta})
    for chunk in retrieval_result.chunks:
        yield SseEvent(type="citation", data={"resource_id": chunk.resource_id, ...})
    yield SseEvent(type="done", data={"finish_reason": "stop"})
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 会话不存在或无权 | 404/403 | CONVERSATION_NOT_FOUND | 会话不存在 |
| AI Service 不可用 | 503 | AI_SERVICE_UNAVAILABLE | 智能服务不可用 |
| LLM 超时 | 504 | LLM_TIMEOUT | 生成超时 |
| 流式中断 | 500 | STREAM_ERROR | 流式中断 |

---

## 8. Web 端适配要点

- Web 端 SSE 通过 `?token=` 传 JWT，Gateway auth 中间件解析
- Gateway 配置 CORS 允许 Flutter Web origin
- 客户端收到 `error` 事件后显示重试按钮
- 断线后重连或降级轮询

---

## 9. 测试策略

- **Gateway 单元测试**：SSE 转发、消息保存、错误处理
- **AI Service 集成测试**：mock 检索与 LLM 验证完整问答流程
- **E2E 测试**：Flutter 上传文件 → 提问 → 验证流式答案

---

## 10. 检查清单

- [ ] Gateway SSE 问答端点
- [ ] AI Service 问答编排
- [ ] 检索 + LLM 流式生成
- [ ] SSE 事件转发与格式化
- [ ] 用户/助手消息持久化
- [ ] 错误处理与降级
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
