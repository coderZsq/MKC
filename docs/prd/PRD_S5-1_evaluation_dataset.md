# PRD：[S5-1] 构建评估数据集

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S3-7_flutter_chat_page.md](./PRD_S3-7_flutter_chat_page.md)、[TECH_S3-7_flutter_chat_page.md](../tech/TECH_S3-7_flutter_chat_page.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-1 |
| **任务名称** | 构建评估数据集 |
| **所属史诗** | E10 评估优化 |
| **故事点** | 3 |
| **优先级** | Could |
| **依赖** | S3-7 Flutter Chat 页面 |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为开发者，我希望基于已完成的知识库问答链路构建 50-100 条标准评估问答对，以便后续用稳定样本评估 RAG 检索、生成、引用与多端问答体验。数据集需要覆盖 MP3、PDF、跨文档问答、摘要、引用跳转与空结果等典型场景，并可在本地与 CI 环境中重复执行。

---

## 验收标准（AC）

- [ ] **AC-1** 提供 50-100 条评估样本，样本覆盖音频、PDF、跨文档、摘要、引用与无答案场景
- [ ] **AC-2** 每条样本包含 `question`、`expected_answer`、`resource_ids`、`expected_citations`、`tags`、`difficulty`
- [ ] **AC-3** 数据集使用 JSONL 或 YAML 格式管理，具备 schema 校验脚本
- [ ] **AC-4** 提供最小 smoke 数据集，CI 可在无外部 LLM Key 时运行结构校验
- [ ] **AC-5** 文档说明样本来源、标注规则、扩充流程与质量门槛
- [ ] **AC-6** 样本不得包含真实密钥、隐私数据或不可公开素材
- [ ] **AC-7** 单元/静态校验覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── eval/
│   ├── datasets/
│   │   ├── rag_eval.jsonl
│   │   └── smoke_eval.jsonl
│   ├── schemas/
│   │   └── eval_case.schema.json
│   └── validate_dataset.py
└── tests/
    └── eval/test_eval_dataset_schema.py
docs/
└── runbooks/
    └── evaluation_dataset.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python | 3.11+ | 数据集校验脚本 |
| pydantic | 2.x | 样本 schema 校验 |
| pytest | 8.x | 数据集结构测试 |

---

## 技术要点

- 评估样本以追加方式维护，禁止依赖线上数据库的隐式状态。
- `expected_citations` 至少包含资源 ID、片段定位、页码或时间戳范围。
- `difficulty` 建议使用 `easy`、`medium`、`hard`，用于后续分层报告。
- smoke 数据集控制在 5-10 条，保证 CI 快速校验。
- 数据集变更必须通过 schema 校验、重复 ID 检查与敏感信息扫描。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 标注样本质量不稳定 | 评估结果失真 | 建立字段约束与人工 review 清单 |
| 样本依赖本地私有文件 | CI 无法复现 | 使用可提交的脱敏 fixture 或 mock resource_id |
| 引用期望过细 | 后续解析格式变化导致大量误报 | 将精确引用与宽松引用分层记录 |

---

## Web 端适配

本任务不涉及 Web 端特殊适配，但样本需要覆盖 Web Chat 页面的典型提问与引用展示场景。

---

## 备注

- 本卡是 S5-2 评估流水线的直接输入。
- 后续可按新增能力继续扩展 tag，如 `web_search`、`agent_compare`、`fallback`。
