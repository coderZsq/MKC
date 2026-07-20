# PRD：[S6-6] 将 QA Service 接入可切换 RAG Engine

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S3-6_sse_qa_api.md](./PRD_S3-6_sse_qa_api.md)、[PRD_S6-2_llamaindex_dependency_config.md](./PRD_S6-2_llamaindex_dependency_config.md)、[PRD_S6-5_llamaindex_retriever_query_engine.md](./PRD_S6-5_llamaindex_retriever_query_engine.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-6 |
| **任务名称** | 将 QA Service 接入可切换 RAG Engine |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S6-5, S3-6 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为用户，我希望问答 API 在切换到 LlamaIndex RAG 后仍保持相同的流式体验、引用展示和错误提示；作为开发者，我希望通过配置在 legacy 与 LlamaIndex 之间切换，以便灰度验证、快速回滚和评估对比。

---

## 验收标准（AC）

- [ ] **AC-1** QA Service 通过 `RAG_ENGINE` 选择 legacy 或 LlamaIndex retrieval engine
- [ ] **AC-2** 两种引擎输出相同 SSE 事件类型：`chunk`、`reasoning`、`citation`、`done`、`error`
- [ ] **AC-3** LlamaIndex 模式下 citation metadata 与 legacy 格式兼容
- [ ] **AC-4** LlamaIndex 检索失败时返回标准 error event，不泄露内部堆栈
- [ ] **AC-5** legacy 模式行为保持不变，现有 QA 测试不需要大改
- [ ] **AC-6** 增加双引擎参数化测试，覆盖成功、空结果、检索异常、引用输出
- [ ] **AC-7** 测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── app/services/rag_engine/
│   ├── factory.py
│   ├── legacy_engine.py
│   └── llamaindex_engine.py
├── app/services/qa_service.py
└── tests/services/
    ├── test_qa_service.py
    └── rag_engine/test_factory.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| LlamaIndex retrieval engine | S6-5 | 新 RAG 内核 |
| legacy RetrievalService | 现有模块 | 默认和回滚引擎 |
| LLMClient | 现有模块 | SSE 流式生成 |

---

## 技术要点

- 抽象统一 `RagEngine.retrieve(request) -> RetrievalResult`。
- QA Service 不直接知道 LlamaIndex 细节，只依赖统一接口。
- SSE 格式、LLM streaming、memory、citation service 尽量不改。
- 所有错误通过现有 `APIException` 或标准错误事件输出。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 双引擎分支污染 QA Service | 代码复杂度上升 | 使用 factory 和统一 protocol |
| LlamaIndex 引用字段缺失 | Flutter 引用显示异常 | S6-3/S6-5 映射测试前置 |
| 回滚不彻底 | 线上不可控 | legacy 默认，配置切回立即生效 |

---

## Web 端适配

Flutter Web 不需要新增 API。验收要求 Web Chat 在两种引擎下均可看到流式答案和引用卡片。

---

## 备注

- 本卡是 Sprint 6 Demo 的核心卡。
- 不在本卡中调整 UI，只保证客户端兼容。
