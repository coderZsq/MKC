# 技术文档：[S5-1] 构建评估数据集

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S5-1_evaluation_dataset.md](../prd/PRD_S5-1_evaluation_dataset.md)

---

## 1. 文档目标

定义评估数据集的文件格式、schema、校验脚本、样本组织方式和测试策略，为 S5-2 离线评估流水线提供稳定输入。

---

## 2. 技术栈

- Python 3.11+
- pydantic 2.x
- pytest 8.x
- JSONL / JSON Schema

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| CLI | `python -m eval.validate_dataset --dataset <path>` | 无 | 校验数据集结构 |

样本示例：

```json
{
  "id": "rag-audio-001",
  "question": "这段音频主要讲了哪些检索优化方法？",
  "expected_answer": "应提到向量检索、重排和引用溯源。",
  "resource_ids": ["res_audio_demo_001"],
  "expected_citations": [{"resource_id": "res_audio_demo_001", "start_sec": 120, "end_sec": 180}],
  "tags": ["audio", "rag", "citation"],
  "difficulty": "medium"
}
```

错误响应以 CLI 输出为主，schema 不合法时返回非 0 退出码。

---

## 4. 配置

```yaml
evaluation_dataset:
  default_path: "ai-service/eval/datasets/rag_eval.jsonl"
  smoke_path: "ai-service/eval/datasets/smoke_eval.jsonl"
  min_cases: 50
  max_cases: 100
  required_tags:
    - audio
    - pdf
    - citation
    - no_answer
```

---

## 5. 模块设计

- `EvalCase`：pydantic 模型，校验字段、枚举和引用结构。
- `DatasetLoader`：逐行读取 JSONL，返回样本列表与行号。
- `DatasetValidator`：检查 ID 唯一、字段完整、tag 覆盖、敏感词。
- `validate_dataset.py`：CLI 入口，输出错误明细。

---

## 6. 关键代码实现

```python
class EvalCase(BaseModel):
    id: str
    question: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)
    resource_ids: list[str]
    expected_citations: list[dict] = []
    tags: list[str]
    difficulty: Literal["easy", "medium", "hard"]

def validate_cases(cases: list[EvalCase]) -> None:
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate eval case id")
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| JSONL 解析失败 | N/A | DATASET_PARSE_FAILED | 数据集 JSONL 解析失败 |
| schema 不合法 | N/A | DATASET_SCHEMA_INVALID | 评估样本字段不合法 |
| 样本数不足 | N/A | DATASET_CASES_TOO_FEW | 评估样本少于最低要求 |
| 存在敏感信息 | N/A | DATASET_SECRET_DETECTED | 数据集疑似包含敏感信息 |

---

## 8. Web 端适配要点

无需 Web 端改动。样本设计需覆盖 Flutter Web Chat 的主流程。

---

## 9. 测试策略

- 单元测试：EvalCase 字段校验、重复 ID、tag 覆盖。
- 集成测试：完整加载 `smoke_eval.jsonl`。
- 静态检查：敏感信息扫描、JSONL 格式检查。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] 测试覆盖率 80%+
- [ ] 数据集说明文档同步更新
