# PRD：[S3-3] 集成 Milvus 向量存储

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S0-2_local_k8s_manifests.md](./PRD_S0-2_local_k8s_manifests.md)、[PRD_S3-2_text_embedding_v3.md](./PRD_S3-2_text_embedding_v3.md)、[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-3 |
| **任务名称** | 集成 Milvus 向量存储 |
| **所属史诗** | E6 知识库检索 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S0-2 本地 K8s 环境 + manifests |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为开发者，我希望将 S3-2 生成的文本向量持久化到 Milvus 向量数据库，并支持按资源 ID、用户 ID 等元数据过滤，以便后续实现高效的语义检索。本任务完成 AI Service 与 Milvus 的集成，包括集合设计、索引构建、向量 CRUD 与连接管理。同时，为降低本地环境门槛，提供 Chroma 内存版作为可选回退。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 启动时自动创建/校验 Milvus collection（若不存在则创建）
- [ ] **AC-2** Collection schema 包含：向量字段、chunk_id、resource_id、user_id、text、metadata JSON、创建时间
- [ ] **AC-3** 支持向量写入（upsert）、删除（按 chunk_id 或 resource_id）、查询（按 ID）
- [ ] **AC-4** 创建 IVF_FLAT 或 HNSW 索引，并配置相似度度量（默认 COSINE）
- [ ] **AC-5** 向量检索支持按 user_id 和 resource_id 做元数据过滤，避免越权访问
- [ ] **AC-6** 提供 Chroma 内存版回退，当 Milvus 不可用时可在配置中切换
- [ ] **AC-7** 连接池与重试：启动失败时重试 3 次，运行时异常不阻塞主流程
- [ ] **AC-8** 单元/集成测试覆盖率 80%+，使用 Milvus Lite 或 mock client 验证 CRUD 与检索

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── vector_store/
│   │   ├── __init__.py
│   │   ├── vector_store.py           # 抽象接口
│   │   ├── milvus_store.py           # Milvus 实现
│   │   └── chroma_store.py           # Chroma 回退实现
│   ├── models/
│   │   └── vector_record.py          # 向量记录模型
│   └── services/
│       └── indexing_service.py       # 索引编排：chunk -> embedding -> store
├── config/
│   └── ai.yaml
└── tests/
    ├── unit/test_milvus_store.py
    ├── unit/test_chroma_store.py
    └── integration/test_indexing_service.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| pymilvus | 2.4.x | Milvus Python SDK |
| milvus-lite | 2.4.x | 本地测试与 CI |
| chromadb | 0.5.x | 内存回退向量库 |
| pydantic | 2.x | 模型校验 |
| tenacity | 8.x | 连接重试 |

---

## 技术要点

### 配置示例

```yaml
vector_store:
  provider: milvus                  # milvus / chroma
  milvus:
    uri: "${MILVUS_URI:http://localhost:19530}"
    token: "${MILVUS_TOKEN:}"
    collection: mkc_chunks
    dimension: 2048
    metric_type: COSINE
    index_type: HNSW
    consistency_level: Bounded
  chroma:
    path: "./data/chroma"
    collection: mkc_chunks
```

### Collection Schema

| 字段 | 类型 | 说明 |
|---|---|---|
| id | VARCHAR(PK) | chunk_id |
| vector | FLOAT_VECTOR(dim) | 归一化向量 |
| resource_id | VARCHAR | 资源 ID |
| user_id | VARCHAR | 用户 ID |
| text | VARCHAR(4096) | 原始文本 |
| metadata | JSON | 页码、时间戳等 |
| created_at | INT64 | 毫秒时间戳 |

### 接口签名

```python
class VectorStore(ABC):
    async def upsert(self, records: list[VectorRecord]) -> None: ...
    async def delete_by_resource(self, resource_id: str) -> None: ...
    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[SearchResult]: ...
```

### 错误处理与降级策略

- Milvus 启动失败：重试 3 次，仍失败则根据配置切换至 Chroma
- 写入失败：记录失败 chunk_id，支持后续重试
- 维度不匹配：启动时校验，不一致则报错退出
- 检索越权：强制传入 user_id 过滤，结果再次校验 resource 归属

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Milvus 本地资源占用高 | 开发机跑不起来 | 使用 Milvus Lite 或 Chroma 回退 |
| 集合/索引创建失败 | 向量无法写入 | 启动时预创建并校验 schema |
| 向量维度与模型不一致 | 写入报错 | 启动时从配置读取 dimensions 并校验 |

---

## Web 端适配

本任务为后端 AI Service 数据层能力，Web 端不直接调用。向量存储为 S3-4 检索与 S3-6 问答提供数据支撑。

---

## 备注

- S3-3 的 schema 需要与 S3-1 的 Chunk 元数据和 S3-2 的 Embedding 维度严格一致
- 建议将资源重新处理时的旧向量删除逻辑抽象为 `reindex_resource(resource_id)`
- 生产环境建议按 user_id 或 resource_id 做 partition 以提升过滤性能
