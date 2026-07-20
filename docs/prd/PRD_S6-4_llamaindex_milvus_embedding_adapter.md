# PRD：[S6-4] 接入 LlamaIndex Milvus VectorStore 与 Embedding 适配器

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S3-2_text_embedding_v3.md](./PRD_S3-2_text_embedding_v3.md)、[PRD_S3-3_milvus_vector_store.md](./PRD_S3-3_milvus_vector_store.md)、[PRD_S6-3_llamaindex_node_metadata_mapping.md](./PRD_S6-3_llamaindex_node_metadata_mapping.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-4 |
| **任务名称** | 接入 LlamaIndex Milvus VectorStore 与 Embedding 适配器 |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S3-2, S3-3 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为开发者，我希望让 LlamaIndex 能复用 MKC 现有 embedding provider 与 Milvus collection，以便不重复建设向量化流程，也不迁移已有索引数据。本任务聚焦 AI Service 内部 adapter，不改变上传、分块和向量写入任务。

---

## 验收标准（AC）

- [ ] **AC-1** 提供 LlamaIndex embedding adapter，内部复用现有 `EmbeddingService.embed_query`
- [ ] **AC-2** 提供 LlamaIndex Milvus VectorStore factory，读取现有 Milvus 配置
- [ ] **AC-3** 支持按 `user_id`、`resource_ids` 构造 metadata filter
- [ ] **AC-4** 不要求重建现有 Milvus collection；collection schema 与 legacy 兼容
- [ ] **AC-5** Milvus 不可用时返回标准 `VECTOR_STORE_UNAVAILABLE` 或 `RETRIEVAL_UNAVAILABLE`
- [ ] **AC-6** 单元测试使用 fake embedding/vector store，集成测试可用 mock Milvus client
- [ ] **AC-7** 测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── app/services/llamaindex/
│   ├── embedding_adapter.py
│   ├── milvus_adapter.py
│   └── filters.py
└── tests/services/llamaindex/
    ├── test_embedding_adapter.py
    └── test_milvus_adapter.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| llama-index-core | S6-2 固定 | Embedding/VectorStore 抽象 |
| llama-index-vector-stores-milvus | 与 core 兼容 | Milvus 接入 |
| pymilvus | 2.x | 现有 Milvus 客户端 |

---

## 技术要点

- Adapter 只做兼容层，不替换 S3 已完成的向量写入流程。
- Embedding 维度必须与现有 Milvus collection 维度一致。
- filter 表达式必须保持用户隔离，任何越权结果需要在 S6-5/S6-6 再防御校验。
- 本卡不决定最终 query engine 行为，只提供 LlamaIndex 能访问已有索引的基础设施。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LlamaIndex Milvus 插件要求不同 schema | 无法复用旧数据 | 优先用自定义 retriever adapter 包装现有 VectorStore |
| Embedding 接口异步/同步差异 | 调用链复杂 | 先实现同步 adapter，与 legacy 保持一致 |
| filter 表达式不兼容 | 用户隔离失效 | 单元测试覆盖多资源和越权场景 |

---

## Web 端适配

本任务不涉及 Web 端特殊适配。

---

## 备注

- 如果官方 Milvus adapter 与现有 schema 不兼容，允许以自定义 LlamaIndex retriever 包装 legacy `VectorStore.search`。
- 不允许在本卡中删除 legacy vector store。
