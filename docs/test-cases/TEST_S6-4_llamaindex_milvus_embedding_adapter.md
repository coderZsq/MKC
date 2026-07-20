# S6-4 测试用例：接入 LlamaIndex Milvus VectorStore 与 Embedding 适配器

## 1. 范围与目标

验证 LlamaIndex embedding adapter、Milvus/vector store adapter、metadata filter、错误映射和旧索引兼容。

## 2. 测试环境

- Python 3.11+
- llama-index-core
- pymilvus mock 或 fake VectorStore
- pytest

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-4-001 | Functional | Unit | P0 | Embedding adapter 调用现有 embed_query | fake embedding service | 调用 query embedding | 返回相同向量 | PRD AC-1 |
| MKC-TC-S6-4-002 | Functional | Unit | P0 | Milvus factory 读取现有配置 | vector config 存在 | 构建 adapter | collection/dimensions 正确 | PRD AC-2 |
| MKC-TC-S6-4-003 | Functional | Unit | P0 | 单资源 filter 正确 | user_id/resource_id | 构造 filter | 包含用户和资源约束 | PRD AC-3 |
| MKC-TC-S6-4-004 | Functional | Unit | P0 | 多资源 filter 正确 | 多个 resource_ids | 构造 filter | 支持资源列表 | PRD AC-3 |
| MKC-TC-S6-4-005 | Functional | Integration | P1 | 旧 collection schema 可复用 | mock legacy schema | 构建 vector store | 不要求重建 collection | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-4-006 | Security | Unit | P0 | filter 必含 user_id | 构造任意请求 | build filter | 缺 user_id 时拒绝或补齐 | PRD AC-3 |
| MKC-TC-S6-4-007 | Security | Static | P1 | 无硬编码 Milvus 密码 | 代码存在 | 搜索 password/token | 无真实密钥 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-4-008 | Negative | Unit | P0 | Embedding 异常映射 | fake service 抛错 | 调用 adapter | 返回 EMBEDDING_UNAVAILABLE | PRD AC-5 |
| MKC-TC-S6-4-009 | Negative | Unit | P0 | Milvus 不可用映射 | mock Milvus 连接失败 | 构建 adapter | 返回 VECTOR_STORE_UNAVAILABLE | PRD AC-5 |
| MKC-TC-S6-4-010 | Negative | Unit | P1 | 空 resource_ids 被拒绝 | resource_ids=[] | build filter | 返回 INVALID_RETRIEVAL_FILTER | PRD AC-3 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-4-011 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S6-4-012 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] embedding adapter 通过
- [ ] vector store adapter 通过
- [ ] filter 含 user/resource
- [ ] 错误映射正确
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
