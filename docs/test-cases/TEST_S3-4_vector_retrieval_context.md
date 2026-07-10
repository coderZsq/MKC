# S3-4 测试用例：实现向量检索 + 上下文组装

## 1. 范围与目标

验证 AI Service 检索与上下文组装模块：问题 Embedding、Top-K 检索、相似度过滤、上下文压缩、Prompt 构建、来源元数据与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- Jinja2 3.1+
- tiktoken 0.7+
- pytest, pytest-cov
- mock Embedding 与 VectorStore

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-4-001 | Functional | Integration | P0 | 检索接口返回 Top-K 块 | 已索引数据 | POST /ai/v1/retrieve | 返回 chunks 与 prompt | PRD AC-1 |
| MKC-TC-S3-4-002 | Functional | Unit | P0 | 对问题生成 Embedding 后检索 | mock EmbeddingService | 调用 RetrievalService.retrieve | 生成 query vector 并调用 store.search | PRD AC-2 |
| MKC-TC-S3-4-003 | Functional | Unit | P0 | 按 resource_ids 过滤 | 配置多个资源 | 调用 retrieve | search 传入 resource_ids 过滤 | PRD AC-3 |
| MKC-TC-S3-4-004 | Functional | Unit | P1 | 相似度阈值过滤 | 配置 threshold=0.7 | 调用 retrieve | 低分块被过滤 | PRD AC-4 |
| MKC-TC-S3-4-005 | Functional | Unit | P1 | 上下文压缩控制 token 数 | 提供大量 chunk | 调用 retrieve | 总 token 不超过 4096 | PRD AC-5 |
| MKC-TC-S3-4-006 | Functional | Unit | P1 | 每个返回块含来源元数据 | 数据带 metadata | 调用 retrieve | 返回块包含 page/timestamp/score | PRD AC-6 |
| MKC-TC-S3-4-007 | Functional | Unit | P2 | Prompt 模板渲染正确 | 提供模板 | 调用 PromptBuilder.build | 渲染后包含上下文与问题 | PRD AC-7 |
| MKC-TC-S3-4-008 | Functional | Unit | P2 | 结果按相关性排序 | 返回多个 score | 调用 retrieve | 结果按 score 降序 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-4-009 | Security | Integration | P0 | 缺少内部 Key 拒绝访问 | 请求头无 Key | POST /ai/v1/retrieve | 返回 401 | TECH 3 |
| MKC-TC-S3-4-010 | Security | Unit | P1 | 无权资源越权访问 | 传入他人 resource_id | 调用 retrieve | 返回 403 | PRD AC-3 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-4-011 | Negative | Integration | P0 | 缺少 question 返回 400 | 请求无 question | POST /ai/v1/retrieve | 返回 INVALID_REQUEST | PRD AC-1 |
| MKC-TC-S3-4-012 | Negative | Unit | P1 | 检索无结果返回空上下文 | 无相关数据 | 调用 retrieve | chunks 为空，prompt 含“无相关知识” | PRD 降级策略 |
| MKC-TC-S3-4-013 | Negative | Unit | P1 | 向量检索失败返回 503 | mock store 异常 | 调用 retrieve | 返回 RETRIEVAL_UNAVAILABLE | PRD 降级策略 |
| MKC-TC-S3-4-014 | Negative | Unit | P1 | 上下文 token 超限截断 | 单 chunk 即超 4096 | 调用 retrieve | 保留最高 chunk，其余截断 | PRD AC-5 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-4-015 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-8 |
| MKC-TC-S3-4-016 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |
| MKC-TC-S3-4-017 | Security | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-4-018 | Compatibility | Unit | P2 | 支持多种 metadata 格式 | 不同来源数据 | 调用 retrieve | 元数据正确保留 | PRD AC-6 |
| MKC-TC-S3-4-019 | Performance | Unit | P2 | 检索总耗时 < 500ms | mock 依赖 | 调用 retrieve | 耗时 < 500ms | 性能基线 |

## 4. 测试执行清单

- [ ] 检索接口端到端
- [ ] Top-K 与相似度过滤
- [ ] 上下文压缩与 Prompt 构建
- [ ] 来源元数据保留
- [ ] 权限与越权
- [ ] 无结果与向量库异常
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
