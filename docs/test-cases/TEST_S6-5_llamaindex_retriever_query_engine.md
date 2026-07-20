# S6-5 测试用例：实现 LlamaIndex Retriever/QueryEngine 封装

## 1. 范围与目标

验证 LlamaIndex RetrievalEngine 对 `RetrievalRequest -> RetrievalResult` 契约的兼容性、过滤、压缩、权限防御和空结果降级。

## 2. 测试环境

- Python 3.11+
- fake LlamaIndex retriever
- pytest

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-5-001 | Functional | Unit | P0 | 输入兼容 RetrievalRequest | fake retriever | 调用 retrieve | 返回 RetrievalResult | PRD AC-1, AC-2 |
| MKC-TC-S6-5-002 | Functional | Unit | P0 | top_k 生效 | fake 返回多节点 | top_k=3 | chunks 数量 <=3 | PRD AC-3 |
| MKC-TC-S6-5-003 | Functional | Unit | P0 | score_threshold 生效 | 节点 score 不同 | threshold=0.8 | 低分结果被过滤 | PRD AC-3 |
| MKC-TC-S6-5-004 | Functional | Unit | P1 | max_context_tokens 生效 | 长文本 chunks | 设置 token 上限 | context_token_count 受控 | PRD AC-3 |
| MKC-TC-S6-5-005 | Functional | Unit | P1 | 多资源候选保留 | 多 resource_ids | retrieve | 至少尝试 per-resource candidate | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-5-006 | Security | Unit | P0 | 越权 resource 被拒绝 | fake 返回未请求 resource | retrieve | 抛 RETRIEVAL_FORBIDDEN | PRD AC-6 |
| MKC-TC-S6-5-007 | Security | Unit | P0 | 越权 user 被拒绝 | fake 返回其他 user_id | retrieve | 抛 RETRIEVAL_FORBIDDEN | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-5-008 | Negative | Unit | P0 | 空结果降级 | fake 返回空 | retrieve | chunks 为空且 prompt 可解释 | PRD AC-5 |
| MKC-TC-S6-5-009 | Negative | Unit | P0 | LlamaIndex 异常映射 | fake retriever 抛错 | retrieve | 返回 RETRIEVAL_UNAVAILABLE | TECH 7 |
| MKC-TC-S6-5-010 | Negative | Unit | P1 | 缺 score 默认过滤安全 | node score None | retrieve | 不崩溃，score=0 | PRD AC-3 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-5-011 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S6-5-012 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] RetrievalResult 契约兼容
- [ ] top_k/threshold/token 生效
- [ ] 权限防御生效
- [ ] 空结果降级
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
