# S5-1 测试用例：构建评估数据集

## 1. 范围与目标

验证评估数据集样本数量、schema、字段完整性、场景覆盖、敏感信息安全和 CI smoke 校验。

## 2. 测试环境

- Python 3.11+
- pydantic 2.x
- pytest 8.x
- JSONL 数据集

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-1-001 | Functional | Static | P0 | 数据集样本数达标 | rag_eval.jsonl 存在 | 运行校验脚本 | 样本数 50-100 | PRD AC-1 |
| MKC-TC-S5-1-002 | Functional | Unit | P0 | 样本字段完整 | 数据集存在 | 校验每行 JSON | 必填字段均存在 | PRD AC-2 |
| MKC-TC-S5-1-003 | Functional | Unit | P0 | schema 校验通过 | schema 已定义 | 运行 validate_dataset | 无 schema 错误 | PRD AC-3 |
| MKC-TC-S5-1-004 | Functional | Static | P1 | 场景 tag 覆盖完整 | 数据集存在 | 统计 tags | 覆盖 audio/pdf/citation/no_answer | PRD AC-1 |
| MKC-TC-S5-1-005 | Functional | Integration | P1 | smoke 数据集可用于 CI | smoke_eval.jsonl 存在 | 运行 smoke 校验 | 退出码为 0 | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-1-006 | Security | Static | P0 | 数据集无硬编码密钥 | 数据集存在 | 扫描 key/token/secret 模式 | 未发现真实密钥 | PRD AC-6 |
| MKC-TC-S5-1-007 | Security | Static | P1 | 样本不含隐私文本 | 数据集存在 | 人工/脚本抽检 | 无个人隐私数据 | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-1-008 | Negative | Unit | P0 | JSONL 解析错误可定位行号 | 构造坏 JSON | 运行校验 | 输出错误行号并非 0 退出 | PRD AC-3 |
| MKC-TC-S5-1-009 | Negative | Unit | P1 | 重复 ID 被拒绝 | 构造重复 ID | 运行校验 | 返回 DATASET_SCHEMA_INVALID | PRD AC-3 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-1-010 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S5-1-011 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] schema 校验通过
- [ ] smoke 数据集可在 CI 运行
- [ ] 覆盖率 80%+
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
