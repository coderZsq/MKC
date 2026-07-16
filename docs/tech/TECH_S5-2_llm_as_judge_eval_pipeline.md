# 技术文档：[S5-2] 实现 LLM-as-judge 评估流水线

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S5-2_llm_as_judge_eval_pipeline.md](../prd/PRD_S5-2_llm_as_judge_eval_pipeline.md)

---

## 1. 文档目标

定义离线评估流水线的执行命令、模块划分、judge 契约、指标计算、报告输出与失败处理。

---

## 2. 技术栈

- Python 3.11+
- Flask/FastAPI 内部问答接口或本地 service 调用
- pydantic 2.x
- httpx 0.27.x
- zhipuai / Kimi SDK
- pytest 8.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| CLI | `python -m eval.pipeline` | 本地环境变量 | 运行离线评估 |
| POST | `/ai/v1/chat` | Internal API Key | 可选：调用现有问答链路 |

CLI 示例：

```bash
python -m eval.pipeline \
  --dataset ai-service/eval/datasets/rag_eval.jsonl \
  --report-dir ai-service/eval/reports \
  --judge mock \
  --tags citation,hard
```

报告输出：

```json
{
  "summary": {
    "recall": 0.82,
    "faithfulness": 0.88,
    "relevance": 0.9,
    "citation_accuracy": 0.76
  },
  "cases": []
}
```

---

## 4. 配置

```yaml
eval:
  judge_provider: mock
  threshold:
    recall: 0.75
    faithfulness: 0.8
    relevance: 0.8
    citation_accuracy: 0.7
  concurrency: 3
  timeout_seconds: 60
  max_retries: 2
```

---

## 5. 模块设计

- `EvalPipeline`：加载样本、调用 answer provider、调用 judge、汇总报告。
- `AnswerProvider`：封装现有 RAG 问答链路，支持 mock。
- `JudgeProvider`：`LLMJudge` 与 `MockJudge` 实现统一评分接口。
- `MetricsCalculator`：计算召回率、忠实度、相关性、引用准确率。
- `ReportWriter`：输出 JSON 与 Markdown。

---

## 6. 关键代码实现

```python
async def run_case(case: EvalCase, answer_provider: AnswerProvider, judge: JudgeProvider) -> EvalResult:
    answer = await answer_provider.answer(case.question, case.resource_ids)
    scores = await judge.score(case=case, answer=answer)
    return EvalResult(case_id=case.id, answer=answer, scores=scores)

def enforce_threshold(summary: EvalSummary, threshold: EvalThreshold) -> int:
    return 1 if summary.any_metric_below(threshold) else 0
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 数据集不存在 | N/A | EVAL_DATASET_NOT_FOUND | 评估数据集不存在 |
| 单题生成失败 | N/A | EVAL_ANSWER_FAILED | 问答链路生成失败 |
| judge 超时 | N/A | EVAL_JUDGE_TIMEOUT | LLM judge 调用超时 |
| 阈值不达标 | N/A | EVAL_THRESHOLD_FAILED | 评估指标低于阈值 |

---

## 8. Web 端适配要点

无需 Web 端改动。报告可后续由静态页面或 Grafana 展示。

---

## 9. 测试策略

- 单元测试：指标计算、阈值判断、报告生成。
- 集成测试：mock answer + mock judge 跑通 smoke 数据集。
- E2E：可选调用本地 AI Service 生成真实报告。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] 测试覆盖率 80%+
- [ ] 评估报告格式文档同步更新
