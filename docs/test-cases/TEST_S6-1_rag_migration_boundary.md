# S6-1 测试用例：梳理现有 RAG 链路并定义 LlamaIndex 迁移边界

## 1. 范围与目标

验证 S6 迁移边界文档覆盖现有 RAG 链路、保留契约、迁移范围、回滚策略和风险清单。

## 2. 测试环境

- Markdown 文档
- markdownlint-cli
- 人工架构 review

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-1-001 | Functional | Static | P0 | RAG 现状链路完整 | TECH 文档存在 | 检查模块列表 | 覆盖 QAService/RetrievalService/VectorStore/Citation/Eval | PRD AC-1 |
| MKC-TC-S6-1-002 | Functional | Static | P0 | 保留契约明确 | TECH 文档存在 | 检查保留项 | Gateway/Flutter/SSE/citation 标记为不变 | PRD AC-2 |
| MKC-TC-S6-1-003 | Functional | Static | P0 | 迁移范围明确 | TECH 文档存在 | 检查可替换模块 | retrieval engine/node mapping/query engine/eval 已列出 | PRD AC-3 |
| MKC-TC-S6-1-004 | Functional | Static | P1 | 回滚策略明确 | TECH 文档存在 | 检查回滚章节 | 包含 `RAG_ENGINE=legacy` | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-1-005 | Security | Static | P0 | 文档无真实密钥 | 文档存在 | 扫描 token/key/secret | 无真实凭据 | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-1-006 | Negative | Static | P1 | 风险清单覆盖核心风险 | 文档存在 | 检查风险表 | 覆盖引用、filter、Milvus、评估、依赖 | PRD AC-5 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-1-007 | Functional | Static | P1 | markdownlint 通过 | 文档存在 | 运行 markdownlint | 0 issues | PRD AC-6 |

## 4. 测试执行清单

- [ ] RAG 边界 review 通过
- [ ] 风险清单完整
- [ ] markdownlint 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
