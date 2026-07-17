# S5-1 评估数据集维护手册

## 文件位置

- 主数据集：`ai-service/eval/datasets/rag_eval.jsonl`
- CI smoke 数据集：`ai-service/eval/datasets/smoke_eval.jsonl`
- JSON Schema：`ai-service/eval/schemas/eval_case.schema.json`
- 校验入口：`python -m eval.validate_dataset --dataset <path>`

## 样本来源

当前样本使用可提交的脱敏 demo resource id，不依赖线上数据库、私有文件或真实用户素材。问题覆盖音频、PDF、跨文档问答、摘要、引用跳转、Web Chat 主流程和无答案安全场景，作为 S5-2 离线评估流水线的稳定输入。

## 标注规则

每行 JSONL 是一个评估样本，必须包含：

- `id`：形如 `rag-audio-001`，全局唯一。
- `question`：用户问题。
- `expected_answer`：期望答案要点，不要求逐字匹配。
- `resource_ids`：样本依赖的资源 ID，可使用脱敏 fixture ID。
- `expected_citations`：能支撑答案的引用。PDF 至少给出 `page` 或 `chunk_id`；音频给出 `start_sec` 和 `end_sec`。
- `tags`：场景标签，例如 `audio`、`pdf`、`cross_document`、`summary`、`citation`、`no_answer`。
- `difficulty`：`easy`、`medium` 或 `hard`。

`no_answer` 样本不得填写 `expected_citations`。引用中的 `resource_id` 必须出现在同一条样本的 `resource_ids` 中。

## 扩充流程

1. 追加 JSONL 行，不重排已有 ID，避免历史评估报告难以对照。
2. 使用脱敏素材或 mock resource id；不要提交真实密钥、个人信息、私有域名或不可公开文本。
3. 为新增样本选择至少一个场景 tag，并保证主数据集总量保持在 50-100 条。
4. 本地运行校验：

```bash
cd ai-service
python -m eval.validate_dataset --dataset eval/datasets/rag_eval.jsonl
python -m eval.validate_dataset --dataset eval/datasets/smoke_eval.jsonl --min-cases 5 --max-cases 10
pytest tests/eval/test_eval_dataset_schema.py
```

## 质量门槛

- 主数据集样本数保持 50-100。
- 必须覆盖 `audio`、`pdf`、`citation`、`no_answer`。
- 所有样本通过 Pydantic schema 校验、重复 ID 检查和敏感信息扫描。
- smoke 数据集保持 5-10 条，且不需要外部 LLM Key。
- 评估样本应描述答案要点和引用位置，避免要求模型逐字复述。

