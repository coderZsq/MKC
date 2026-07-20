# PRD：[S6-3] 实现 LlamaIndex Document/Node 元数据映射

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S3-1_text_chunking.md](./PRD_S3-1_text_chunking.md)、[PRD_S4-5_answer_citation_tracing.md](./PRD_S4-5_answer_citation_tracing.md)、[PRD_S6-2_llamaindex_dependency_config.md](./PRD_S6-2_llamaindex_dependency_config.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-3 |
| **任务名称** | 实现 LlamaIndex Document/Node 元数据映射 |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S3-1, S4-5 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为开发者，我希望将 MKC 现有 `VectorRecord`、`VectorSearchResult` 和 `RetrievalChunk` 映射为 LlamaIndex Document/Node，同时完整保留引用跳转所需 metadata，以便 LlamaIndex 检索结果仍能被现有 citation formatter 和 Flutter 引用卡片消费。

---

## 验收标准（AC）

- [ ] **AC-1** 提供从 `VectorRecord` 到 LlamaIndex Node 的映射函数
- [ ] **AC-2** 提供从 LlamaIndex Node/NodeWithScore 到 `RetrievalChunk` 的反向映射函数
- [ ] **AC-3** metadata 保留 `resource_id`、`user_id`、`chunk_id`、`page`、`start_sec`、`end_sec`、`source_type`
- [ ] **AC-4** 文本为空、metadata 缺字段、score 缺失时有安全默认值
- [ ] **AC-5** 映射逻辑不读取外部服务，单元测试可纯内存运行
- [ ] **AC-6** 单元测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── app/services/llamaindex/
│   ├── __init__.py
│   ├── metadata_mapper.py
│   └── models.py
└── tests/services/llamaindex/
    └── test_metadata_mapper.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| llama-index-core | S6-2 固定 | Document、TextNode、NodeWithScore |
| pydantic | 2.x | 现有模型校验 |
| pytest | 8.x | 单元测试 |

---

## 技术要点

- LlamaIndex Node 的 `id_` 应使用现有 chunk/vector record id，避免引用链路丢失。
- metadata 中的权限字段必须保留，但不能写入 prompt 中不需要的敏感信息。
- page/timestamp 字段使用现有 citation schema，避免 Flutter 引用卡片新增分支。
- 映射层是无副作用 adapter，不负责 embedding、存储或检索。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| metadata 字段命名不统一 | 引用跳转失效 | 在 mapper 中统一规范字段名 |
| Node score 兼容差异 | 排序和阈值异常 | score 缺失时默认 0.0，并在 S6-5 处理阈值 |
| 文本截断策略不一致 | Prompt 质量波动 | 映射层不截断，仍由检索/压缩层控制 |

---

## Web 端适配

本任务不涉及 Web 端代码改动，但必须保证输出 citation metadata 与现有 Flutter 引用卡片兼容。

---

## 备注

- 本卡是 S6-4、S6-5 的基础。
- 后续如引入新 source type，应先扩展 mapper 测试。
