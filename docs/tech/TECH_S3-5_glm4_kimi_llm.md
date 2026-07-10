# 技术文档：[S3-5] 接入智谱 GLM-4 / Kimi 生成答案

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S3-5_glm4_kimi_llm.md](../prd/PRD_S3-5_glm4_kimi_llm.md)

---

## 1. 文档目标

定义 AI Service 中 LLM 生成模块的技术实现：统一客户端接口、智谱 GLM-4 与 Kimi provider、同步/流式调用、重试、错误处理与测试策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- zhipuai 2.x
- openai 1.30+
- tenacity 8.x
- pydantic 2.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/llm/complete` | Internal API Key | 同步生成 |
| POST | `/ai/v1/llm/stream` | Internal API Key | SSE 流式生成 |

### 请求示例

```json
POST /ai/v1/llm/stream
Headers: X-Internal-Key: <key>
{
  "messages": [
    {"role": "system", "content": "你是知识库助手"},
    {"role": "user", "content": "本次会议的议题是什么？"}
  ],
  "temperature": 0.7,
  "max_tokens": 2048
}
```

### 流式响应示例

```text
event: message
data: {"delta": "本次", "finish_reason": null}

event: message
data: {"delta": "会议", "finish_reason": null}

event: done
data: {"finish_reason": "stop"}

```

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
llm:
  provider: zhipuai
  model: glm-4-flash
  api_key: "${ZHIPU_API_KEY}"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  temperature: 0.7
  max_tokens: 2048
  timeout: 60
  max_retries: 3
```

---

## 5. 模块设计

### 5.1 LLMClient

```python
class LLMClient:
    async def complete(self, request: LLMRequest) -> LLMResponse: ...
    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]: ...
```

### 5.2 ZhipuProvider

```python
class ZhipuProvider(BaseLLMProvider):
    async def stream_complete(self, request: LLMRequest):
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[m.model_dump() for m in request.messages],
            stream=True,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            yield LLMStreamChunk(delta=delta, finish_reason=chunk.choices[0].finish_reason)
```

### 5.3 KimiProvider

- 使用 OpenAI 兼容客户端

---

## 6. 关键代码实现

### 6.1 统一 SSE 格式化

```python
async def format_sse_stream(stream: AsyncIterator[LLMStreamChunk]):
    async for chunk in stream:
        data = chunk.model_dump_json(exclude_none=True)
        yield f"event: message\ndata: {data}\n\n"
    yield "event: done\ndata: {\"finish_reason\": \"stop\"}\n\n"
```

### 6.2 重试

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def complete(self, request: LLMRequest) -> LLMResponse:
    ...
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| API Key 无效 | 401 | LLM_AUTH_FAILED | LLM 认证失败 |
| 模型不可用 | 503 | LLM_UNAVAILABLE | LLM 服务不可用 |
| 流式中断 | 500 | LLM_STREAM_ERROR | 流式输出中断 |
| 超时 | 504 | LLM_TIMEOUT | LLM 调用超时 |

---

## 8. Web 端适配要点

LLM 接口为内部接口，流式输出通过 S3-6 的 SSE 问答 API 转发给 Web 端。事件格式需与 Gateway SSE 协议对齐。

---

## 9. 测试策略

- **单元测试**：provider 选择、请求构建、重试逻辑
- **集成测试**：mock 流式响应验证 SSE 格式
- **Mock 策略**：本地 mock provider 返回固定文本流

---

## 10. 检查清单

- [ ] `LLMClient` 统一接口
- [ ] 智谱 GLM-4 provider
- [ ] Kimi / OpenAI 兼容 provider
- [ ] 同步与流式调用
- [ ] 重试与超时
- [ ] SSE 事件格式化
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
