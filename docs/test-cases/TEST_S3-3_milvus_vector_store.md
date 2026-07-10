# S3-3 测试用例：集成 Milvus 向量存储

## 1. 范围与目标

验证 AI Service 向量存储模块：Milvus 集合创建、索引、写入、删除、检索、元数据过滤、Chroma 回退与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- pymilvus 2.4+
- milvus-lite 2.4+（测试）
- chromadb 0.5+
- pytest, pytest-cov

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-3-001 | Functional | Unit | P0 | 启动时自动创建 Milvus collection | Milvus Lite 已启动 | 初始化 MilvusStore | collection 存在，schema 正确 | PRD AC-1 |
| MKC-TC-S3-3-002 | Functional | Unit | P0 | 批量写入向量记录 | 提供 10 条记录 | 调用 upsert | 写入成功 | PRD AC-3 |
| MKC-TC-S3-3-003 | Functional | Unit | P0 | 语义检索返回 Top-K | 已写入 10 条记录 | 调用 search(top_k=5) | 返回 5 条结果 | PRD AC-4 |
| MKC-TC-S3-3-004 | Functional | Unit | P1 | 按 user_id 过滤 | 不同用户数据 | 调用 search(filters={user_id: u1}) | 仅返回 u1 数据 | PRD AC-5 |
| MKC-TC-S3-3-005 | Functional | Unit | P1 | 按 resource_ids 过滤 | 多资源数据 | 调用 search(filters={resource_ids: [r1]}) | 仅返回 r1 数据 | PRD AC-5 |
| MKC-TC-S3-3-006 | Functional | Unit | P1 | 按 resource_id 删除 | 已写入记录 | 调用 delete_by_resource | 该资源记录被删除 | PRD AC-3 |
| MKC-TC-S3-3-007 | Functional | Unit | P2 | 创建 HNSW 索引 | collection 存在 | 初始化 MilvusStore | 索引存在且类型为 HNSW | PRD AC-4 |
| MKC-TC-S3-3-008 | Functional | Unit | P2 | 切换到 Chroma 回退 | 配置 provider=chroma | 初始化 ChromaStore | 写入/检索成功 | PRD AC-6 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-3-009 | Security | Integration | P0 | 缺少内部 Key 拒绝访问 | 请求头无 Key | POST /ai/v1/vectors | 返回 401 | TECH 3 |
| MKC-TC-S3-3-010 | Security | Unit | P1 | 越权检索被过滤 | 以 userA 查询 userB 数据 | 调用 search | 结果不包含 userB 数据 | PRD AC-5 |
| MKC-TC-S3-3-011 | Security | Static | P1 | 无硬编码 Milvus token | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-3-012 | Negative | Unit | P0 | 写入维度不匹配报错 | 记录维度=1024，配置=2048 | 调用 upsert | 抛出 DIMENSION_MISMATCH | PRD AC-4 |
| MKC-TC-S3-3-013 | Negative | Unit | P1 | Milvus 连接失败重试 | mock 连接失败 2 次 | 初始化 MilvusStore | 第 3 次成功 | PRD AC-7 |
| MKC-TC-S3-3-014 | Negative | Unit | P1 | 全部重试失败切换 Chroma | Milvus 完全不可用 | 初始化 | 切换至 Chroma 并可用 | PRD AC-6 |
| MKC-TC-S3-3-015 | Negative | Unit | P1 | 空记录 upsert | 传入空列表 | 调用 upsert | 无操作，不抛异常 | PRD AC-3 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-3-016 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-8 |
| MKC-TC-S3-3-017 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-3-018 | Compatibility | Unit | P2 | Milvus 与 Chroma 结果格式一致 | 写入相同数据 | 分别检索 | SearchResult 字段一致 | PRD AC-6 |
| MKC-TC-S3-3-019 | Performance | Unit | P2 | 1000 条记录检索 < 100ms | Milvus Lite | 调用 search | 耗时 < 100ms | 性能基线 |

## 4. 测试执行清单

- [ ] Milvus collection 与索引创建
- [ ] 批量写入与删除
- [ ] 语义检索与过滤
- [ ] 权限与越权过滤
- [ ] Chroma 回退
- [ ] 错误处理与重试
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
