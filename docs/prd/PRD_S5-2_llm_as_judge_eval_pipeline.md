# PRD：[S5-2] 实现 LLM-as-judge 评估流水线

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S5-1_evaluation_dataset.md](./PRD_S5-1_evaluation_dataset.md)、[TECH_S5-1_evaluation_dataset.md](../tech/TECH_S5-1_evaluation_dataset.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-2 |
| **任务名称** | 实现 LLM-as-judge 评估流水线 |
| **所属史诗** | E10 评估优化 |
| **故事点** | 5 |
| **优先级** | Could |
| **依赖** | S5-1 构建评估数据集 |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为开发者，我希望能一键运行 LLM-as-judge 评估流水线，衡量知识库问答在召回率、忠实度、相关性与引用准确率上的表现，以便在模型、检索、Prompt 或重排策略调整后快速判断质量变化。本任务只面向离线评估与内部报告，不直接影响线上回答链路。

---

## 验收标准（AC）

- [ ] **AC-1** 支持读取 S5-1 数据集并批量调用现有 RAG 问答链路生成答案
- [ ] **AC-2** 输出召回率、忠实度、相关性、引用准确率四类核心指标
- [ ] **AC-3** LLM judge prompt 固化到版本化模板，支持 mock judge 在 CI 中运行
- [ ] **AC-4** 评估结果输出 JSON 与 Markdown 报告，包含逐题明细和总体汇总
- [ ] **AC-5** 支持按 tag、difficulty、resource_type 过滤评估样本
- [ ] **AC-6** 失败样本可重试，单题失败不终止整批评估
- [ ] **AC-7** 评估阈值可配置，低于阈值时命令返回非 0 退出码
- [ ] **AC-8** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── eval/
│   ├── pipeline.py
│   ├── judges/
│   │   ├── base.py
│   │   ├── llm_judge.py
│   │   └── mock_judge.py
│   ├── metrics.py
│   ├── report.py
│   └── prompts/
│       └── judge_v1.md
└── tests/
    └── eval/
        ├── test_metrics.py
        └── test_pipeline.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python | 3.11+ | 评估流水线 |
| pydantic | 2.x | 评估输入输出模型 |
| httpx | 0.27.x | 调用内部问答接口或模型 API |
| zhipuai / Kimi SDK | 2.x / latest | LLM judge |
| pytest | 8.x | 测试 |

---

## 技术要点

- 评估命令示例：`python -m eval.pipeline --dataset eval/datasets/rag_eval.jsonl --tags citation,hard`。
- judge 输出必须是结构化 JSON，包含 `score`、`reason`、`evidence` 字段。
- 指标聚合时同时保留 micro average、按 tag 分组结果与失败列表。
- 线上回答 API、检索服务或 mock runner 均可作为 answer provider。
- judge 请求需要超时、重试和成本保护，默认并发数不超过 3。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LLM judge 评分波动 | 报告不稳定 | 固化 prompt、temperature=0、保留 reason 便于人工复核 |
| 外部模型 Key 缺失 | CI 无法执行 | 提供 mock judge 与小样本 smoke 模式 |
| 评估耗时过长 | 开发反馈慢 | 支持过滤、并发限制与断点重跑 |

---

## Web 端适配

本任务不涉及 Web 端特殊适配。评估结果可后续作为内部质量报告在文档或 Grafana 中展示。

---

## 备注

- 本卡产出的报告为 S5 项目复盘和技术博客提供量化依据。
- 评估流水线不应写入生产会话或用户消息表。
