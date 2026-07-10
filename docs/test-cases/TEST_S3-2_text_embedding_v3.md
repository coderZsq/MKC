# S3-2 测试用例：集成 text-embedding-v3 生成 Embedding

## 1. 范围与目标

验证 AI Service Embedding 模块：智谱 provider、批量处理、重试、维度校验、归一化、错误处理与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- zhipuai 2.x
- openai 1.30+
- tenacity 8.x
- pytest, pytest-cov
- Redis（可选）

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-2-001 | Functional | Unit | P0 | 批量生成 Embedding | 提供 10 个 Chunk | 调用 EmbeddingService.embed | 返回 10 个等长向量 | PRD AC-1 |
| MKC-TC-S3-2-002 | Functional | Integration | P0 | 调用智谱 text-embedding-v3 | 配置 provider=zhipuai | POST /ai/v1/embed | 返回 2048 维向量 | PRD AC-2 |
| MKC-TC-S3-2-003 | Functional | Unit | P1 | 批量拆分超出 batch_size | 配置 batch_size=4，提供 10 个 Chunk | 调用 embed | 分 3 批次调用 provider | PRD AC-3 |
| MKC-TC-S3-2-004 | Functional | Unit | P1 | 输出向量与输入顺序一致 | 提供 5 个 Chunk | 调用 embed | 输出顺序与输入一致 | PRD AC-6 |
| MKC-TC-S3-2-005 | Functional | Unit | P1 | 向量归一化 | 配置 normalize=true | 调用 embed | 向量模长为 1 | PRD AC-2 |
| MKC-TC-S3-2-006 | Functional | Unit | P2 | 维度校验通过 | 配置 dimensions=2048 | 调用 embed | 返回向量长度 2048 | PRD AC-2 |
| MKC-TC-S3-2-007 | Functional | Integration | P2 | 支持 OpenAI 兼容 provider | 配置 provider=openai | POST /ai/v1/embed | 返回向量 | PRD AC-2 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-2-008 | Security | Integration | P0 | 缺少内部 Key 拒绝访问 | 请求头无 Key | POST /ai/v1/embed | 返回 401 | TECH 3 |
| MKC-TC-S3-2-009 | Security | Static | P1 | 无硬编码 API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | PRD AC-7 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-2-010 | Negative | Unit | P0 | 空批次返回空列表 | 传入空列表 | 调用 embed | 返回空列表 | PRD AC-4 |
| MKC-TC-S3-2-011 | Negative | Unit | P1 | API Key 缺失启动失败 | 未设置 ZHIPU_API_KEY | 启动服务 | 报错拒绝启动 | PRD AC-7 |
| MKC-TC-S3-2-012 | Negative | Unit | P1 | 单批次失败重试 3 次 | mock provider 前两次失败 | 调用 embed | 第三次成功 | PRD AC-5 |
| MKC-TC-S3-2-013 | Negative | Unit | P1 | 全部批次失败抛异常 | mock provider 始终失败 | 调用 embed | 抛出 EMBEDDING_UNAVAILABLE | PRD AC-5 |
| MKC-TC-S3-2-014 | Negative | Unit | P1 | 维度不匹配报错 | 配置 dimensions=1024，实际返回 2048 | 调用 embed | 返回 DIMENSION_MISMATCH | PRD AC-2 |
| MKC-TC-S3-2-015 | Negative | Unit | P1 | 空字符串过滤 | 提供空文本 Chunk | 调用 embed | 空文本被过滤或返回 0 向量 | PRD AC-4 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-2-016 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-8 |
| MKC-TC-S3-2-017 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-2-018 | Compatibility | Unit | P2 | Mock provider 返回固定向量 | 配置 provider=mock | 调用 embed | 返回固定维度向量 | PRD AC-7 |
| MKC-TC-S3-2-019 | Performance | Integration | P2 | 100 个 Chunk 5s 内完成 | 使用 mock provider | POST /ai/v1/embed | 总耗时 < 5s | 性能基线 |

## 4. 测试执行清单

- [ ] 批量 Embedding 生成
- [ ] 智谱 provider 集成
- [ ] 批量拆分与重试
- [ ] 维度校验与归一化
- [ ] 空文本与错误处理
- [ ] 认证与权限
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
