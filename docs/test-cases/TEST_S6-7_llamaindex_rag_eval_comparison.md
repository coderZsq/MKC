# S6-7 测试用例：增加 LlamaIndex RAG 评估对比脚本

## 1. 范围与目标

验证 legacy 与 LlamaIndex RAG 评估对比脚本的 CLI、报告、delta 计算、阈值门禁和安全输出。

## 2. 测试环境

- Python 3.11+
- S5 smoke eval 数据集
- mock answer provider
- mock judge
- pytest

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-7-001 | Functional | Integration | P0 | CLI 可运行双引擎 | smoke 数据集存在 | compare --engines legacy,llamaindex | 两套结果生成 | PRD AC-1 |
| MKC-TC-S6-7-002 | Functional | Unit | P0 | summary metrics 分引擎输出 | 构造评估结果 | 生成 summary | 每个 engine 都有指标 | PRD AC-2 |
| MKC-TC-S6-7-003 | Functional | Unit | P0 | delta 报告正确标记 | 构造 base/candidate | 计算 delta | improved/regressed/unchanged 正确 | PRD AC-3 |
| MKC-TC-S6-7-004 | Functional | Integration | P1 | mock judge 无外部 Key 可运行 | judge=mock | 运行 smoke | 退出码 0 | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-7-005 | Security | Static | P0 | 报告不包含 API Key | 设置假环境变量 | 运行报告生成 | 报告无 key/token/secret | PRD AC-6 |
| MKC-TC-S6-7-006 | Security | Static | P1 | 报告不输出完整私有 prompt | 生成真实报告 | 检查字段 | 仅输出必要摘要或截断 prompt | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-7-007 | Negative | Unit | P0 | 指标回归触发非 0 | candidate 低于容忍度 | 运行 gate | 返回 EVAL_REGRESSION_DETECTED | PRD AC-5 |
| MKC-TC-S6-7-008 | Negative | Unit | P1 | 未知 engine 被拒绝 | engines=bad | 运行 CLI | 返回 EVAL_ENGINE_INVALID | TECH 7 |
| MKC-TC-S6-7-009 | Negative | Integration | P1 | 单引擎失败不影响报告结构 | llamaindex runner 抛错 | 运行 compare | legacy 结果保留，失败被记录 | PRD AC-2 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-7-010 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S6-7-011 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] compare CLI 通过
- [ ] delta 报告正确
- [ ] 回归门禁可失败
- [ ] mock judge 可运行
- [ ] 报告无密钥
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
