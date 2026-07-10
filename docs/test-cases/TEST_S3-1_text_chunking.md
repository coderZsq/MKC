# S3-1 测试用例：文本分块策略实现

## 1. 范围与目标

验证 AI Service 文本分块模块：三种分块策略、元数据保留、重叠窗口、边界条件、配置化与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- tiktoken 0.7+
- PyYAML 6+
- pytest, pytest-cov
- mypy, ruff

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-1-001 | Functional | Unit | P0 | 段落分块按空行切分 | 提供含空行文本 | 调用 ParagraphChunker.split | 返回按段落分块，每块语义完整 | PRD AC-1 |
| MKC-TC-S3-1-002 | Functional | Unit | P0 | 固定 token 分块按长度切分 | 提供超长文本 | 调用 FixedTokenChunker.split | 每块 token 数不超过 512 | PRD AC-4 |
| MKC-TC-S3-1-003 | Functional | Unit | P1 | 语义分块按标题切分 | 提供 Markdown 标题文本 | 调用 SemanticChunker.split | 块边界不破坏章节标题 | PRD AC-1 |
| MKC-TC-S3-1-004 | Functional | Unit | P1 | 相邻块存在重叠窗口 | 配置 overlap=50 | 切分超长文本 | 相邻块起始位置差 < chunk_size | PRD AC-3 |
| MKC-TC-S3-1-005 | Functional | Unit | P1 | 每个分块保留元数据 | 传入 resource_id/page | 调用任意 chunker | 返回块包含完整 metadata | PRD AC-2 |
| MKC-TC-S3-1-006 | Functional | Integration | P1 | ChunkingService 根据策略分发 | 配置 strategy=paragraph | 调用 service.chunk | 使用 ParagraphChunker | PRD AC-1 |
| MKC-TC-S3-1-007 | Functional | Unit | P2 | 中文文本正确估算 | 提供中文文本 | 调用 FixedTokenChunker | 按字/词混合估算，不超出限制 | PRD AC-5 |
| MKC-TC-S3-1-008 | Functional | Unit | P2 | 配置化切换策略 | 修改 ai.yaml strategy | 重新加载服务 | 默认策略生效 | PRD AC-7 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-1-009 | Security | Integration | P0 | 缺少内部 Key 拒绝访问 | 请求头无 Key | POST /ai/v1/chunk | 返回 401 | TECH 3 |
| MKC-TC-S3-1-010 | Security | Integration | P1 | 错误 Key 拒绝访问 | 使用错误 Key | POST /ai/v1/chunk | 返回 403 | TECH 3 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-1-011 | Negative | Unit | P0 | 空文本返回空列表 | 传入空字符串 | 调用 chunker | 返回空列表，不抛异常 | PRD AC-6 |
| MKC-TC-S3-1-012 | Negative | Integration | P1 | 不支持策略返回 400 | strategy=unknown | POST /ai/v1/chunk | 返回 INVALID_STRATEGY | PRD AC-1 |
| MKC-TC-S3-1-013 | Negative | Unit | P1 | 超长无分隔符文本强制截断 | 提供 10k 字符无空格 | 调用 FixedTokenChunker | 返回多个块，记录警告 | PRD AC-6 |
| MKC-TC-S3-1-014 | Reliability | Unit | P1 | tiktoken 失败时字符数降级 | mock tiktoken 异常 | 调用 chunker | 使用字符数估算继续 | PRD 降级策略 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-1-015 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-8 |
| MKC-TC-S3-1-016 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |
| MKC-TC-S3-1-017 | Security | Static | P1 | 无硬编码 API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-1-018 | Compatibility | Unit | P2 | 三种策略输出格式一致 | 同一段文本 | 分别调用三种 chunker | Chunk 模型字段一致 | PRD AC-2 |
| MKC-TC-S3-1-019 | Performance | Unit | P2 | 1 万字文本 1s 内完成 | 提供 1 万字 | 调用 service.chunk | 耗时 < 1s | 性能基线 |

## 4. 测试执行清单

- [ ] 三种分块策略功能正确
- [ ] 重叠窗口与元数据保留
- [ ] 边界场景处理
- [ ] 配置化策略加载
- [ ] 认证与权限
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
