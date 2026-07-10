# 技术文档：[S3-2] 集成 text-embedding-v3 生成 Embedding

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S3-2_text_embedding_v3.md](../prd/PRD_S3-2_text_embedding_v3.md)

---

## 1. 文档目标

定义 AI Service 中 Embedding 生成模块的技术实现：统一接口、智谱 provider、批量处理、重试、维度校验与测试策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- zhipuai 2.x
- openai 1.30+
- tenacity 8.x
- pydantic 2.x
- numpy 1.26.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/embed` | Internal API Key | 提交文本块生成 Embedding |

### 请求示例

```json
POST /ai/v1/embed
Headers: X-Internal-Key: <key>
{
  "chunks": [
    {"id": "chunk-1", "resource_id": "res-1", "text": "..."}
  ]
}
```

### 响应示例

```json
{
  "embeddings": [
    {
      "chunk_id": "chunk-1",
      "resource_id": "res-1",
      "vector": [0.12, -0.05, ...],
      "model": "embedding-3",
      "dimensions": 2048
    }
  ]
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | EMPTY_BATCH | 空批次 |
| 401 | EMBEDDING_AUTH_FAILED | API Key 无效 |
| 503 | EMBEDDING_UNAVAILABLE | Embedding 服务不可用 |
| 500 | EMBEDDING_INTERNAL_ERROR | 内部错误 |

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
embedding:
  provider: zhipuai
  model: embedding-3
  api_key: "${ZHIPU_API_KEY}"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  batch_size: 64
  max_retries: 3
  timeout: 30
  dimensions: 2048
  normalize: true
```

环境变量：

- `ZHIPU_API_KEY`
- `KIMI_API_KEY`
- `EMBEDDING_PROVIDER`

---

## 5. 模块设计

### 5.1 EmbeddingService

```python
class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider, config: EmbeddingConfig):
        self._provider = provider
        self._config = config

    async def embed(self, chunks: list[Chunk]) -> list[Embedding]:
        ...
```

### 5.2 EmbeddingProvider

```python
class EmbeddingProvider(ABC):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

### 5.3 ZhipuEmbeddingProvider

```python
class ZhipuEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: EmbeddingConfig):
        self._client = ZhipuAI(api_key=config.api_key)
        self._config = config

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self._config.model,
            input=texts,
        )
        return [item.embedding for item in response.data]
```

### 5.4 MockEmbeddingProvider

- 返回固定维度随机向量，用于 CI 与本地开发

---

## 6. 关键代码实现

### 6.1 批量与重试

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class EmbeddingService:
    async def embed(self, chunks: list[Chunk]) -> list[Embedding]:
        if not chunks:
            return []

        embeddings = []
        for i in range(0, len(chunks), self._config.batch_size):
            batch = chunks[i:i + self._config.batch_size]
            vectors = await self._embed_batch([c.text for c in batch])
            for chunk, vector in zip(batch, vectors):
                embeddings.append(Embedding(
                    chunk_id=chunk.id,
                    resource_id=chunk.resource_id,
                    vector=self._normalize(vector) if self._config.normalize else vector,
                    model=self._config.model,
                    dimensions=len(vector),
                ))
        return embeddings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._provider.embed(texts)
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| API Key 无效 | 401 | EMBEDDING_AUTH_FAILED | Embedding 认证失败 |
| 单批次失败 | 503 | EMBEDDING_UNAVAILABLE | Embedding 服务不可用 |
| 维度不匹配 | 500 | DIMENSION_MISMATCH | 向量维度与配置不符 |
| 空批次 | 400 | EMPTY_BATCH | 输入为空 |

---

## 8. Web 端适配要点

Embedding 接口为内部接口，不暴露给 Web 端。向量为后端检索使用。

---

## 9. 测试策略

- **单元测试**：批量分片、归一化、维度校验、重试逻辑
- **集成测试**：使用 mock provider 调用 `/ai/v1/embed`
- **Mock 策略**：固定返回 2048 维随机向量，验证映射正确

---

## 10. 检查清单

- [ ] `EmbeddingService` 统一入口
- [ ] 智谱 provider 实现
- [ ] 批量处理与重试
- [ ] 向量归一化与维度校验
- [ ] Mock provider 支持本地开发
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
