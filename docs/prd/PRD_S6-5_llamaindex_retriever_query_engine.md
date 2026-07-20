# PRD：[S6-5] 实现 LlamaIndex Retriever/QueryEngine 封装

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S6-3_llamaindex_node_metadata_mapping.md](./PRD_S6-3_llamaindex_node_metadata_mapping.md)、[PRD_S6-4_llamaindex_milvus_embedding_adapter.md](./PRD_S6-4_llamaindex_milvus_embedding_adapter.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-5 |
| **任务名称** | 实现 LlamaIndex Retriever/QueryEngine 封装 |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S6-3, S6-4 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为开发者，我希望封装一个符合 MKC `RetrievalRequest -> RetrievalResult` 契约的 LlamaIndex Retriever/QueryEngine，以便 QA Service 可以像调用 legacy retrieval 一样调用 LlamaIndex，并获得同样结构的 chunks、prompt 和 token count。

---

## 验收标准（AC）

- [ ] **AC-1** 新增 LlamaIndex retrieval engine，输入兼容 `RetrievalRequest`
- [ ] **AC-2** 输出兼容 `RetrievalResult`，包含 `chunks`、`prompt`、`context_token_count`
- [ ] **AC-3** 支持 `top_k`、`score_threshold`、`max_context_tokens`、`resource_ids` 过滤
- [ ] **AC-4** 多资源查询至少保留每个资源候选召回的能力，避免单资源挤占
- [ ] **AC-5** 空结果时返回可解释 prompt 或空 chunks，不抛未知异常
- [ ] **AC-6** 对越权或 filter 失效结果执行防御校验
- [ ] **AC-7** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── app/services/llamaindex/
│   ├── retrieval_engine.py
│   ├── query_engine.py
│   └── context_compressor.py
└── tests/services/llamaindex/
    ├── test_retrieval_engine.py
    └── test_query_engine.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| llama-index-core | S6-2 固定 | Retriever/QueryEngine |
| Milvus adapter | S6-4 | 召回节点 |
| TokenEstimator | 现有模块 | 上下文 token 控制 |

---

## 技术要点

- QueryEngine 不直接生成最终答案，S6-6 仍由现有 LLM streaming 负责回答。
- Prompt 输出应尽量复用现有 `PromptBuilder`，减少 prompt 行为差异。
- LlamaIndex 结果先映射为 `RetrievalChunk`，再进入 citation validator。
- 如果 LlamaIndex 官方 QueryEngine 难以维持 SSE/citation 契约，优先实现 retriever-only 方案。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| QueryEngine 自动生成答案 | 破坏现有 SSE 流 | 限定本卡只负责 retrieval/prompt，不负责 streaming answer |
| 多资源召回质量下降 | 跨文档问答变差 | 保留 per-resource candidate 策略 |
| score 语义差异 | 阈值误杀 | 在测试中固定 score 映射规则 |

---

## Web 端适配

本任务不涉及 Web 端代码改动。输出结构必须兼容现有 Chat SSE 和引用卡片。

---

## 备注

- 本卡完成后，S6-6 才将其接入 QA Service。
- S6-7 将使用评估数据集对比 legacy 与 LlamaIndex 检索效果。
