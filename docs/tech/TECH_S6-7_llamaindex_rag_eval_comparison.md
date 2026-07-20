# 技术文档：[S6-7] 增加 LlamaIndex RAG 评估对比脚本

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-7_llamaindex_rag_eval_comparison.md](../prd/PRD_S6-7_llamaindex_rag_eval_comparison.md)

---

## 1. 文档目标

定义 legacy 与 LlamaIndex RAG 的离线评估对比 CLI、报告格式、阈值门禁和测试策略。

---

## 2. 技术栈

- Python 3.11+
- S5 eval pipeline
- pydantic 2.x
- pytest

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| CLI | `python -m eval.compare_engines` | 本地环境变量 | 对比多个 RAG engine |

示例：

```bash
python -m eval.compare_engines \
  --dataset ai-service/eval/datasets/smoke_eval.jsonl \
  --engines legacy,llamaindex \
  --judge mock \
  --report-dir ai-service/eval/reports
```

---

## 4. 配置

```yaml
eval_compare:
  engines: ["legacy", "llamaindex"]
  regression_tolerance:
    recall: 0.03
    faithfulness: 0.03
    citation_accuracy: 0.05
```

---

## 5. 模块设计

- `EngineRunner`：用指定 engine 调用 answer provider。
- `ComparisonPipeline`：按 engine 分组运行评估。
- `DeltaReporter`：生成 per-case 和 summary delta。
- `ThresholdGate`：判断是否回归。

---

## 6. 关键代码实现

```python
def compare_summaries(base: EvalSummary, candidate: EvalSummary) -> ComparisonSummary:
    return ComparisonSummary(
        recall_delta=candidate.recall - base.recall,
        faithfulness_delta=candidate.faithfulness - base.faithfulness,
        citation_accuracy_delta=candidate.citation_accuracy - base.citation_accuracy,
    )
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 未知 engine | N/A | EVAL_ENGINE_INVALID | 评估引擎不合法 |
| 单引擎评估失败 | N/A | EVAL_ENGINE_FAILED | 引擎评估失败 |
| 指标回归 | N/A | EVAL_REGRESSION_DETECTED | RAG 指标出现回归 |

---

## 8. Web 端适配要点

无需 Web 端改动。

---

## 9. 测试策略

- 单元测试：delta 计算、阈值判断、报告生成。
- 集成测试：mock engine + mock judge 跑通 smoke。
- 安全测试：报告不包含 API Key。

---

## 10. 检查清单

- [ ] compare CLI 已实现
- [ ] JSON/Markdown 报告已生成
- [ ] 回归门禁已实现
- [ ] mock 模式 CI 可运行
- [ ] 测试覆盖率 80%+
