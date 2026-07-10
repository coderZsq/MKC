# 技术文档：[S3-3] 集成 Milvus 向量存储

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S3-3_milvus_vector_store.md](../prd/PRD_S3-3_milvus_vector_store.md)

---

## 1. 文档目标

定义 AI Service 中向量存储模块的技术实现：抽象接口、Milvus 与 Chroma 双实现、集合设计、索引、CRUD、检索与回退策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- pymilvus 2.4.x
- milvus-lite 2.4.x（测试）
- chromadb 0.5.x
- pydantic 2.x
- tenacity 8.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/vectors` | Internal API Key | 批量写入向量 |
| DELETE | `/ai/v1/vectors/resources/{resource_id}` | Internal API Key | 按资源删除 |
| POST | `/ai/v1/vectors/search` | Internal API Key | 语义检索 |

### 请求/响应示例

```json
POST /ai/v1/vectors
{
  "records": [
    {
      "chunk_id": "chunk-1",
      "resource_id": "res-1",
      "user_id": "user-1",
      "text": "...",
      "vector": [0.1, ...],
      "metadata": {"page": 3}
    }
  ]
}
```

```json
POST /ai/v1/vectors/search
{
  "vector": [0.1, ...],
  "top_k": 5,
  "filters": {"user_id": "user-1", "resource_ids": ["res-1"]}
}
```

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
vector_store:
  provider: milvus
  milvus:
    uri: "${MILVUS_URI:http://localhost:19530}"
    token: "${MILVUS_TOKEN:}"
    collection: mkc_chunks
    dimension: 2048
    metric_type: COSINE
    index_type: HNSW
  chroma:
    path: "./data/chroma"
    collection: mkc_chunks
```

---

## 5. 模块设计

### 5.1 VectorStore

```python
class VectorStore(ABC):
    async def upsert(self, records: list[VectorRecord]) -> None: ...
    async def delete_by_resource(self, resource_id: str) -> None: ...
    async def search(self, vector: list[float], top_k: int, filters: dict | None) -> list[SearchResult]: ...
```

### 5.2 MilvusStore

- 启动时创建 collection
- 创建 HNSW index
- 使用 `MilvusClient` 简化操作

### 5.3 ChromaStore

- 本地持久化
- 作为 Milvus 不可用时回退

---

## 6. 关键代码实现

### 6.1 Milvus 集合创建

```python
from pymilvus import MilvusClient, DataType

class MilvusStore(VectorStore):
    def __init__(self, config: MilvusConfig):
        self._client = MilvusClient(uri=config.uri, token=config.token)
        self._collection = config.collection
        self._dimension = config.dimension
        self._ensure_collection()

    def _ensure_collection(self):
        if self._client.has_collection(self._collection):
            return
        schema = self._client.create_schema(auto_id=False)
        schema.add_field("id", DataType.VARCHAR, max_length=64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=self._dimension)
        schema.add_field("resource_id", DataType.VARCHAR, max_length=64)
        schema.add_field("user_id", DataType.VARCHAR, max_length=64)
        schema.add_field("text", DataType.VARCHAR, max_length=4096)
        schema.add_field("metadata", DataType.JSON)
        schema.add_field("created_at", DataType.INT64)
        self._client.create_collection(self._collection, schema=schema)
        self._client.create_index(
            self._collection,
            index_params={"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 64}},
        )
```

### 6.2 检索

```python
async def search(self, vector, top_k, filters):
    expr = self._build_expr(filters)
    results = self._client.search(
        collection_name=self._collection,
        data=[vector],
        limit=top_k,
        filter=expr,
        output_fields=["resource_id", "text", "metadata", "created_at"],
    )
    return [SearchResult(**r) for r in results[0]]
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| Milvus 连接失败 | 503 | VECTOR_STORE_UNAVAILABLE | 向量存储不可用 |
| 维度不匹配 | 500 | DIMENSION_MISMATCH | 向量维度不匹配 |
| 集合创建失败 | 500 | COLLECTION_CREATE_FAILED | 集合创建失败 |
| 越权检索 | 403 | FORBIDDEN | 无权访问该资源 |

---

## 8. Web 端适配要点

向量存储为后端能力，不直接暴露给 Web 端。检索结果通过问答 API 间接返回。

---

## 9. 测试策略

- **单元测试**：Milvus Lite 内存版 CRUD、Chroma 回退、过滤表达式构建
- **集成测试**：写入 → 检索 → 删除全链路
- **Mock 策略**：mock `MilvusClient` 验证接口调用

---

## 10. 检查清单

- [ ] `VectorStore` 抽象接口
- [ ] Milvus 集合与索引创建
- [ ] 向量写入、删除、检索
- [ ] 元数据过滤
- [ ] Chroma 回退
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
