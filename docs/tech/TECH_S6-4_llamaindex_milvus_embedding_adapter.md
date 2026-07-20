# 技术文档：[S6-4] 接入 LlamaIndex Milvus VectorStore 与 Embedding 适配器

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-4_llamaindex_milvus_embedding_adapter.md](../prd/PRD_S6-4_llamaindex_milvus_embedding_adapter.md)

---

## 1. 文档目标

定义 LlamaIndex 与 MKC 现有 embedding provider、Milvus vector store 的适配方式，使新 RAG 引擎复用既有向量索引。

---

## 2. 技术栈

- Python 3.11+
- llama-index-core
- llama-index-vector-stores-milvus
- pymilvus
- pytest

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 类 | `MKCEmbeddingAdapter` | 内部 | LlamaIndex embedding 接口适配 |
| 工厂 | `build_llamaindex_vector_store()` | 内部 | 构建 Milvus vector store |

---

## 4. 配置

复用现有 Milvus 与 embedding 配置：

```yaml
vector_store:
  provider: milvus
  collection_name: mkc_chunks
  dimensions: 1024

embedding:
  provider: mock
```

---

## 5. 模块设计

- `embedding_adapter.py`：将现有 `embed_query` 包装为 LlamaIndex embedding。
- `milvus_adapter.py`：优先使用官方 Milvus vector store；不兼容时包装现有 `VectorStore.search`。
- `filters.py`：统一生成 `user_id/resource_ids` 过滤表达式。

---

## 6. 关键代码实现

```python
class MKCEmbeddingAdapter(BaseEmbedding):
    def __init__(self, embedding_service: EmbeddingServiceProtocol) -> None:
        self._embedding = embedding_service

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embedding.embed_query(query)


def build_metadata_filters(user_id: str, resource_ids: list[str]) -> dict[str, Any]:
    return {"user_id": user_id, "resource_ids": resource_ids}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| Embedding 失败 | 503 | EMBEDDING_UNAVAILABLE | 向量生成不可用 |
| Milvus 连接失败 | 503 | VECTOR_STORE_UNAVAILABLE | 向量存储不可用 |
| Filter 构造失败 | 400 | INVALID_RETRIEVAL_FILTER | 检索过滤条件不合法 |

---

## 8. Web 端适配要点

无需 Web 端改动。

---

## 9. 测试策略

- 单元测试：embedding adapter 调用现有 service。
- 单元测试：filter 覆盖单资源、多资源、空资源。
- 集成测试：mock Milvus client 返回节点并映射为 chunk。

---

## 10. 检查清单

- [ ] Embedding adapter 已实现
- [ ] Milvus adapter 已实现或明确 fallback wrapper
- [ ] metadata filter 已测试
- [ ] 测试覆盖率 80%+
