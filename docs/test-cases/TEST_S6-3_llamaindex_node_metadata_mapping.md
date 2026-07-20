# S6-3 测试用例：实现 LlamaIndex Document/Node 元数据映射

## 1. 范围与目标

验证 MKC VectorRecord、VectorSearchResult、RetrievalChunk 与 LlamaIndex Node/NodeWithScore 的映射正确性和 citation metadata 兼容性。

## 2. 测试环境

- Python 3.11+
- llama-index-core
- pytest

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-3-001 | Functional | Unit | P0 | VectorRecord 转 TextNode | 构造完整 record | 调用 mapper | node id/text/metadata 正确 | PRD AC-1 |
| MKC-TC-S6-3-002 | Functional | Unit | P0 | NodeWithScore 转 RetrievalChunk | 构造 node score | 调用反向 mapper | chunk 字段完整 | PRD AC-2 |
| MKC-TC-S6-3-003 | Functional | Unit | P0 | citation metadata 完整保留 | metadata 含 page/timestamp | 执行双向映射 | 字段不丢失 | PRD AC-3 |
| MKC-TC-S6-3-004 | Functional | Unit | P1 | 映射逻辑纯内存运行 | 无外部服务 | 运行单测 | 不访问 Milvus/LLM | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-3-005 | Security | Unit | P0 | user_id/resource_id 保留供权限校验 | record 含用户和资源 | 映射为 node | metadata 包含 user_id/resource_id | PRD AC-3 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-3-006 | Negative | Unit | P1 | score 缺失默认 0 | node score=None | 反向映射 | score=0.0 | PRD AC-4 |
| MKC-TC-S6-3-007 | Negative | Unit | P1 | 文本为空不报错 | record text 为空 | 映射 | node text 为空字符串 | PRD AC-4 |
| MKC-TC-S6-3-008 | Negative | Unit | P1 | 可选 metadata 缺失降级 | metadata 无 page/time | 反向映射 | chunk 可生成 | PRD AC-4 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-3-009 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-6 |
| MKC-TC-S6-3-010 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] 正反向映射通过
- [ ] citation metadata 保留
- [ ] 缺字段降级
- [ ] 权限字段保留
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
