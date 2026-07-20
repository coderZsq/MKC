# PRD：[S6-1] 梳理现有 RAG 链路并定义 LlamaIndex 迁移边界

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)、[PRD_S4-5_answer_citation_tracing.md](./PRD_S4-5_answer_citation_tracing.md)、[PRD_S5-2_llm_as_judge_eval_pipeline.md](./PRD_S5-2_llm_as_judge_eval_pipeline.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-1 |
| **任务名称** | 梳理现有 RAG 链路并定义 LlamaIndex 迁移边界 |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S3, S4, S5-2 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为开发者，我希望先梳理 MKC 现有 RAG 链路的输入、输出、引用、评估和回滚边界，以便后续引入 LlamaIndex 时不破坏 Gateway、Flutter、SSE 和引用跳转等既有契约。本任务只产出迁移设计与风险清单，不直接改变线上 RAG 行为。

---

## 验收标准（AC）

- [ ] **AC-1** 文档列出现有 RAG 链路的关键模块、数据模型、调用路径和 SSE 事件契约
- [ ] **AC-2** 明确哪些模块保持不变：Gateway API、Flutter Chat、QA SSE 事件、citation schema
- [ ] **AC-3** 明确 LlamaIndex 迁移范围：AI Service 内部 retrieval engine、node mapping、query engine、评估对比
- [ ] **AC-4** 输出 legacy 与 LlamaIndex 双引擎切换策略和回滚条件
- [ ] **AC-5** 输出迁移风险清单，覆盖引用丢失、metadata filter、Milvus schema、评估波动和依赖体积
- [ ] **AC-6** 文档通过 markdownlint，且不包含真实密钥、私有 URL 或不可公开素材

---

## 推荐目录结构

```text
docs/
├── prd/PRD_S6-1_rag_migration_boundary.md
├── tech/TECH_S6-1_rag_migration_boundary.md
├── test-cases/TEST_S6-1_rag_migration_boundary.md
└── runbooks/
    └── llamaindex_migration.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| LlamaIndex | 0.10+ / 0.11+ | 后续 S6 RAG 引擎迁移目标 |
| Milvus | 2.x | 现有向量存储 |
| pytest | 8.x | 后续迁移边界回归测试 |

---

## 技术要点

- 现有公开契约不在 S6-1 修改，S6-1 只定义迁移边界。
- LlamaIndex 应作为 AI Service 内部可替换 RAG Engine，不能要求 Gateway 或 Flutter 改协议。
- 引用 metadata 必须继续携带 `resource_id`、`chunk_id`、页码、时间戳和 score。
- 默认迁移策略为双引擎并行：legacy 保持默认，LlamaIndex 先通过配置和评估验证。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 边界未定义清楚 | 后续任务互相踩接口 | 先冻结 API/SSE/citation 外部契约 |
| 现有实现与文档不一致 | 迁移方案失真 | 以当前代码和测试为准补充差异 |
| LlamaIndex 版本差异大 | 后续依赖选择摇摆 | S6-2 再固定依赖版本和开关 |

---

## Web 端适配

本任务不涉及 Web 端代码改动。迁移边界要求 Flutter Web Chat 页无需感知 legacy/LlamaIndex 的切换。

---

## 备注

- 本卡是 S6-2 到 S6-8 的设计入口。
- 若发现现有 RAG 契约缺口，应记录为风险或后续卡，不在 S6-1 中直接重构。
