# S5-5 测试用例：接入 LangSmith / Langfuse

## 1. 范围与目标

验证 LLM observer 抽象、provider 切换、事件记录、脱敏、第三方不可用降级和配置文档。

## 2. 测试环境

- Python 3.11+
- pytest
- mock Langfuse/LangSmith client
- mock LLMClient

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-5-001 | Functional | Unit | P0 | LLMClient 调用 observer | observer 注入 | 调用 LLM 生成 | record_generation 被调用 | PRD AC-1 |
| MKC-TC-S5-5-002 | Functional | Unit | P1 | provider 可切换 | 配置 langfuse/langsmith | 初始化 factory | 返回对应 provider | PRD AC-2 |
| MKC-TC-S5-5-003 | Functional | Unit | P0 | 事件包含关键元数据 | mock LLM 调用 | 检查事件 | 包含 prompt_version/model/token/status | PRD AC-3 |
| MKC-TC-S5-5-004 | Functional | Integration | P1 | noop 默认可用 | provider=none | 调用 LLM | 问答正常无远端写入 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-5-005 | Security | Unit | P0 | prompt 脱敏和截断 | 输入含密钥/长文本 | 调用 redactor | 输出含 REDACTED 且长度受控 | PRD AC-4 |
| MKC-TC-S5-5-006 | Security | Static | P0 | 日志无第三方密钥 | 运行 observer | 扫描日志 | 无 LANGFUSE_SECRET_KEY 等明文 | PRD AC-4 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-5-007 | Negative | Unit | P0 | provider 不可用降级 | mock client 抛错 | 调用 observer | LLM 主流程不失败 | PRD AC-5 |
| MKC-TC-S5-5-008 | Negative | Unit | P1 | 配置缺失降级 noop | 缺少 API Key | 初始化 provider | 返回 noop 并记录 WARN | PRD AC-5 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-5-009 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S5-5-010 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] provider factory 测试通过
- [ ] 脱敏测试通过
- [ ] 第三方失败不影响问答
- [ ] 覆盖率 80%+
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
