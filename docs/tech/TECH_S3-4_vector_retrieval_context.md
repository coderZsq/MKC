# 技术文档：[S3-4] 实现向量检索 + 上下文组装

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S3-4_vector_retrieval_context.md](../prd/PRD_S3-4_vector_retrieval_context.md)

---

## 1. 文档目标

定义 AI Service 中检索与上下文组装模块的技术实现：检索接口、Embedding 查询、Top-K 过滤、上下文压缩、Prompt 构建与测试策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- Jinja2 3.1.x
- tiktoken 0.7.x
- pydantic 2.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/retrieve` | Internal API Key | 检索相关文本块并返回上下文 |

### 请求示例

```json
POST /ai/v1/retrieve
Headers: X-Internal-Key: <key>
{
  "question": "本次会议的议题是什么？",
  "user_id": "user-1",
  "resource_ids": ["res-1"],
  "top_k": 5,
  "score_threshold": 0.7
}
```

### 响应示例

```json
{
  "chunks": [
    {
      "chunk_id": "chunk-1",
      "resource_id": "res-1",
      "text": "本次会议主要讨论了...",
      "score": 0.89,
      "metadata": {"page": 3}
    }
  ],
  "prompt": "基于以下上下文...",
  "context_token_count": 1200
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | INVALID_REQUEST | 缺少 question 或 resource_ids |
| 403 | FORBIDDEN | 无权访问资源 |
| 503 | RETRIEVAL_UNAVAILABLE | 检索服务不可用 |

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
retrieval:
  default_top_k: 5
  score_threshold: 0.7
  max_context_tokens: 4096
  prompt_template: "prompts/rag.txt"
```

---

## 5. 模块设计

### 5.1 RetrievalService

```python
class RetrievalService:
    def __init__(self, embedding_svc, vector_store, prompt_builder):
        self._embedding_svc = embedding_svc
        self._vector_store = vector_store
        self._prompt_builder = prompt_builder

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        query_vector = await self._embedding_svc.embed_query(request.question)
        chunks = await self._vector_store.search(query_vector, request.top_k, filters={
            "user_id": request.user_id,
            "resource_ids": request.resource_ids,
        })
        filtered = [c for c in chunks if c.score >= request.score_threshold]
        compressed = self._compress_context(filtered)
        prompt = self._prompt_builder.build(compressed, request.question)
        return RetrievalResult(chunks=compressed, prompt=prompt)
```

### 5.2 PromptBuilder

```python
class PromptBuilder:
    def __init__(self, template_path: str):
        self._template = Environment().from_string(Path(template_path).read_text())

    def build(self, chunks: list[Chunk], question: str) -> str:
        return self._template.render(chunks=chunks, question=question)
```

---

## 6. 关键代码实现

### 6.1 上下文压缩

```python
import tiktoken

class RetrievalService:
    def _compress_context(self, chunks: list[SearchResult]) -> list[SearchResult]:
        encoder = tiktoken.get_encoding("cl100k_base")
        total = 0
        selected = []
        for chunk in chunks:
            tokens = len(encoder.encode(chunk.text))
            if total + tokens > self._max_context_tokens:
                break
            selected.append(chunk)
            total += tokens
        return selected
```

### 6.2 Prompt 模板

```jinja2
你是知识库助手。请基于以下上下文回答用户问题。
{% for chunk in chunks %}
[{{ loop.index }}] {{ chunk.text }} （来源：{{ chunk.metadata }}）
{% endfor %}

用户问题：{{ question }}
请给出简洁、准确的回答。
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 缺少 question | 400 | INVALID_REQUEST | 缺少问题 |
| 资源越权 | 403 | FORBIDDEN | 无权访问资源 |
| 向量检索失败 | 503 | RETRIEVAL_UNAVAILABLE | 检索不可用 |
| 无检索结果 | 200 | - | 返回空上下文 |

---

## 8. Web 端适配要点

检索接口为内部接口，由 Gateway 问答服务调用。Web 端通过问答 SSE 间接消费。

---

## 9. 测试策略

- **单元测试**：上下文压缩、Prompt 构建、过滤阈值
- **集成测试**：mock Embedding 与 VectorStore 验证检索流程
- **Mock 策略**：固定 query vector 与固定返回结果

---

## 10. 检查清单

- [ ] `RetrievalService` 检索编排
- [ ] `PromptBuilder` 模板渲染
- [ ] Top-K 与相似度阈值过滤
- [ ] 上下文 token 压缩
- [ ] 来源元数据保留
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
