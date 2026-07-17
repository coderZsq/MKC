# S5-2 LLM-as-judge 评估流水线

## 本地运行

使用 mock answer provider 与 mock judge，可在无外部 LLM Key 的环境中运行：

```bash
cd ai-service
python -m eval.pipeline \
  --dataset eval/datasets/smoke_eval.jsonl \
  --report-dir eval/reports \
  --judge mock \
  --answer-provider mock \
  --min-cases 5 \
  --max-cases 10
```

主数据集运行：

```bash
python -m eval.pipeline \
  --dataset eval/datasets/rag_eval.jsonl \
  --report-dir eval/reports \
  --judge mock \
  --answer-provider mock
```

## 过滤样本

支持按 tag、difficulty 和 resource type 过滤：

```bash
python -m eval.pipeline \
  --dataset eval/datasets/rag_eval.jsonl \
  --report-dir eval/reports \
  --tags citation \
  --difficulty hard \
  --resource-type pdf
```

多个值使用逗号分隔，tag 与 resource type 使用 OR 语义。

## 阈值门禁

默认阈值：

- recall: `0.75`
- faithfulness: `0.8`
- relevance: `0.8`
- citation_accuracy: `0.7`

任何指标低于阈值时，命令返回非 0：

```bash
python -m eval.pipeline \
  --dataset eval/datasets/smoke_eval.jsonl \
  --report-dir eval/reports \
  --threshold-relevance 0.99
```

## 报告输出

每次运行会在 `--report-dir` 下输出：

- `eval_report_<timestamp>.json`
- `eval_report_<timestamp>.md`

报告包含总体四项指标、按 tag 分组指标、逐题答案、引用、评分、失败样本和错误码。报告写入前会扫描 `api_key`、`secret`、`token`、`password` 等敏感标记，避免把凭据写入评估产物。

