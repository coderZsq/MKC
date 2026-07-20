# S6-8 测试用例：更新 RAG 架构文档与调试 Runbook

## 1. 范围与目标

验证 Sprint 6 架构文档和 LlamaIndex RAG Runbook 的完整性、命令可执行性、链接有效性、回滚步骤和 Web smoke 描述。

## 2. 测试环境

- markdownlint-cli
- markdown-link-check
- 本地 shell
- AI Service 可选 smoke 环境

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-8-001 | Functional | Static | P0 | ARCHITECTURE 更新双引擎 | 架构文档存在 | 检查 Chat/RAG Flow | 包含 legacy/LlamaIndex 双引擎 | PRD AC-1 |
| MKC-TC-S6-8-002 | Functional | Static | P0 | Runbook 包含配置步骤 | Runbook 存在 | 检查 RAG_ENGINE | legacy/llamaindex 均说明 | PRD AC-2 |
| MKC-TC-S6-8-003 | Functional | Static | P1 | Runbook 包含 metadata/citation 注意事项 | Runbook 存在 | 检查章节 | 说明字段和引用兼容 | PRD AC-3 |
| MKC-TC-S6-8-004 | Functional | Static | P1 | Runbook 包含 Demo 检查命令 | Runbook 存在 | 检查命令 | 含 QA smoke/eval compare/web smoke | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-8-005 | Security | Static | P0 | 文档无真实密钥 | 文档存在 | 搜索 key/token/secret | 无真实凭据 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-8-006 | Negative | Static | P0 | 常见故障覆盖完整 | Runbook 存在 | 检查故障章节 | 覆盖依赖/Milvus/filter/citation/eval | PRD AC-4 |
| MKC-TC-S6-8-007 | Negative | Static | P1 | 回滚步骤清晰 | Runbook 存在 | 检查 rollback | 3 步内切回 legacy 并验证 | PRD AC-2 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-8-008 | Functional | Static | P0 | markdownlint 通过 | 文档存在 | 运行 markdownlint | 0 issues | PRD AC-6 |
| MKC-TC-S6-8-009 | Functional | Static | P0 | markdown-link-check 通过 | 文档存在 | 运行链接检查 | 0 broken links | PRD AC-6 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-8-010 | Compatibility | Static | P1 | Runbook 包含 Flutter Web smoke | Runbook 存在 | 检查 Web 章节 | 含启动、提问、引用检查步骤 | PRD Web 端适配 |

## 4. 测试执行清单

- [ ] 架构文档更新
- [ ] Runbook 完整
- [ ] 回滚步骤可执行
- [ ] Web smoke 描述完整
- [ ] markdownlint 通过
- [ ] link check 通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
