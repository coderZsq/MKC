# PRD：[S6-7] 增加 LlamaIndex RAG 评估对比脚本

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S5-1_evaluation_dataset.md](./PRD_S5-1_evaluation_dataset.md)、[PRD_S5-2_llm_as_judge_eval_pipeline.md](./PRD_S5-2_llm_as_judge_eval_pipeline.md)、[PRD_S6-6_qa_service_dual_rag_engine.md](./PRD_S6-6_qa_service_dual_rag_engine.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-7 |
| **任务名称** | 增加 LlamaIndex RAG 评估对比脚本 |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 3 |
| **优先级** | Should |
| **依赖** | S5-1, S5-2, S6-6 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为开发者，我希望用同一套评估数据集分别运行 legacy 与 LlamaIndex RAG，并生成差异报告，以便判断 LlamaIndex 是否真正提升召回、忠实度、相关性和引用准确率，而不是只完成技术迁移。

---

## 验收标准（AC）

- [ ] **AC-1** 新增 CLI 支持 `--engines legacy,llamaindex` 批量评估
- [ ] **AC-2** 输出两套引擎的 summary metrics 和逐题结果
- [ ] **AC-3** 输出 delta 报告，标记 improved/regressed/unchanged cases
- [ ] **AC-4** 支持 mock judge 和 smoke 数据集，CI 无外部 Key 可运行
- [ ] **AC-5** 支持阈值门禁：LlamaIndex 指标低于 legacy 指定容忍度时返回非 0
- [ ] **AC-6** 报告不包含真实 API Key、完整私有 prompt 或敏感环境变量
- [ ] **AC-7** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── eval/
│   ├── compare_engines.py
│   ├── engine_runner.py
│   └── reports/
└── tests/eval/
    ├── test_engine_comparison.py
    └── test_compare_cli.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| S5 eval pipeline | 现有模块 | 数据集、judge、指标 |
| QA dual engine | S6-6 | 两套 RAG 输出 |
| pytest | 8.x | 测试 |

---

## 技术要点

- 对比脚本应尽量复用 S5-2 评估流水线，不复制 judge 和 metric 逻辑。
- 每条 case 必须记录 engine、latency、answer、citations、scores 和 error。
- delta 报告关注“是否回归”，而不是要求 LlamaIndex 每项都更高。
- 支持只跑 smoke 数据集，方便 PR CI 快速验证。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| judge 波动导致误判 | 回归判断不稳定 | CI 默认 mock judge，真实 judge 报告人工 review |
| 评估耗时过长 | 开发反馈慢 | 支持 tags、limit、smoke |
| 两套引擎输出格式不一致 | 报告生成失败 | S6-6 统一 answer provider 输出模型 |

---

## Web 端适配

本任务不涉及 Web 端特殊适配。

---

## 备注

- 本卡输出可作为 S6 是否切默认引擎的重要依据。
- 评估报告可在 S6-8 Runbook 中说明阅读方式。
