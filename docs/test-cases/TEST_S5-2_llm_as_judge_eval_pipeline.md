# S5-2 测试用例：实现 LLM-as-judge 评估流水线

## 1. 范围与目标

验证评估流水线的数据读取、RAG 调用、LLM/mock judge、指标计算、报告生成、阈值失败和异常隔离。

## 2. 测试环境

- Python 3.11+
- pytest, pytest-cov
- mock answer provider
- mock judge provider
- S5-1 smoke 数据集

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-2-001 | Functional | Integration | P0 | 流水线读取数据集并生成答案 | smoke 数据集存在 | 运行 eval pipeline | 每条样本生成 answer | PRD AC-1 |
| MKC-TC-S5-2-002 | Functional | Unit | P0 | 指标计算正确 | 构造评分结果 | 调用 metrics | 四类指标输出正确 | PRD AC-2 |
| MKC-TC-S5-2-003 | Functional | Unit | P0 | mock judge 可运行 | 配置 judge=mock | 运行评估 | 无需外部 Key 也成功 | PRD AC-3 |
| MKC-TC-S5-2-004 | Functional | Integration | P1 | 输出 JSON 与 Markdown 报告 | report-dir 存在 | 运行评估 | 生成两种报告 | PRD AC-4 |
| MKC-TC-S5-2-005 | Functional | Unit | P1 | 按 tag 过滤样本 | 数据集含多个 tag | 使用 --tags citation | 仅评估匹配样本 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-2-006 | Security | Static | P0 | 报告不包含 API Key | 运行评估 | 扫描报告 | 无密钥明文 | PRD AC-3 |
| MKC-TC-S5-2-007 | Security | Unit | P1 | judge prompt 不输出敏感配置 | mock 敏感环境变量 | 运行 prompt 构造 | prompt 不含密钥 | 安全要求 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-2-008 | Negative | Unit | P0 | 单题失败不终止整批 | answer provider 单题抛错 | 运行评估 | 记录失败并继续 | PRD AC-6 |
| MKC-TC-S5-2-009 | Negative | Unit | P1 | judge 超时可重试 | mock timeout | 运行评估 | 重试后记录失败 | PRD AC-6 |
| MKC-TC-S5-2-010 | Negative | Integration | P0 | 指标低于阈值退出非 0 | 配置高阈值 | 运行评估 | 命令返回非 0 | PRD AC-7 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-2-011 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-8 |
| MKC-TC-S5-2-012 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] smoke pipeline 通过
- [ ] JSON/Markdown 报告生成
- [ ] 阈值失败返回非 0
- [ ] 覆盖率 80%+
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
