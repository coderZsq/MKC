# PRD：[S6-8] 更新 RAG 架构文档与调试 Runbook

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S6-6_qa_service_dual_rag_engine.md](./PRD_S6-6_qa_service_dual_rag_engine.md)、[PRD_S6-7_llamaindex_rag_eval_comparison.md](./PRD_S6-7_llamaindex_rag_eval_comparison.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-8 |
| **任务名称** | 更新 RAG 架构文档与调试 Runbook |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 2 |
| **优先级** | Should |
| **依赖** | S6-6 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为开发者和维护者，我希望更新架构文档和调试 Runbook，说明 legacy/LlamaIndex 双引擎的配置、数据流、评估、排障和回滚方式，以便后续开发 MCP 与 Skill 时能稳定复用新的 RAG 内核。

---

## 验收标准（AC）

- [ ] **AC-1** 更新 `docs/ARCHITECTURE.md` 中 Chat/RAG Flow，体现双引擎结构
- [ ] **AC-2** 新增或更新 Runbook，说明 `RAG_ENGINE` 配置、验证命令和回滚步骤
- [ ] **AC-3** 文档包含 LlamaIndex metadata/citation 注意事项
- [ ] **AC-4** 文档包含常见故障：依赖缺失、Milvus filter 异常、引用为空、评估回归
- [ ] **AC-5** 文档列出 Sprint 6 Demo 检查命令
- [ ] **AC-6** markdownlint 和 markdown-link-check 通过

---

## 推荐目录结构

```text
docs/
├── ARCHITECTURE.md
└── runbooks/
    └── llamaindex_rag.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| markdownlint-cli | latest | Markdown 格式校验 |
| markdown-link-check | latest | 链接校验 |

---

## 技术要点

- 文档应基于最终实现，不夸大未完成能力。
- Runbook 需要写清楚 legacy 和 LlamaIndex 的切换命令。
- 回滚步骤必须短：修改环境变量、重启 AI Service、运行 smoke QA。
- 故障排查优先列日志关键词、配置字段和测试命令。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 文档提前于实现 | 内容不准确 | S6-8 放在 S6-6 后执行 |
| Runbook 缺少可执行命令 | 排障价值低 | 每个关键场景给出命令 |
| 链接失效 | CI 失败 | 运行 markdown-link-check |

---

## Web 端适配

本任务不涉及 Web 端代码改动，但 Runbook 应包含 Flutter Web Chat smoke 验证步骤。

---

## 备注

- S6-8 是 Sprint 6 收尾卡。
- 后续 S7/S8 文档可链接本 Runbook 说明 RAG 能力底座。
