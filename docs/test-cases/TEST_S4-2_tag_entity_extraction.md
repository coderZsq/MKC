# S4-2 测试用例：实现标签/实体抽取

## 1. 范围与目标

验证标签/实体抽取服务：LLM JSON mode 抽取、标签去重归一化、实体类型校验、规则降级、空内容兜底、异步任务、接口认证、存储持久化与代码质量。

## 2. 测试环境

- Python 3.11+
- 智谱 GLM-4 / Kimi API key（集成测试）
- MySQL 测试库
- Celery 测试 broker
- Mock LLM provider（单元测试）

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-2-001 | Functional | Unit | P0 | LLM 抽取 5-10 个关键词标签 | Mock LLM 返回 10 个标签 | 调用 llm_provider.extract | 返回 5-10 个标签 | PRD AC-2 |
| MKC-TC-S4-2-002 | Functional | Unit | P0 | LLM 抽取命名实体 | Mock LLM 返回实体列表 | 调用 llm_provider.extract | 返回实体含 text/type/mention | PRD AC-3 |
| MKC-TC-S4-2-003 | Functional | Unit | P0 | 标签去重与归一化 | 标签含重复项与同义词 | 调用 tag_normalizer.normalize | 去重、同义词合并、数量 5-10 | PRD AC-4 |
| MKC-TC-S4-2-004 | Functional | Unit | P0 | LLM JSON mode 结构化输出 | Mock LLM 返回 JSON | 解析响应 | 字段为 tags 与 entities | PRD AC-5 |
| MKC-TC-S4-2-005 | Functional | Integration | P0 | 标签存储到 resource_tags | 提供 resource_id 与标签 | 调用 tag_repository.upsert 后查询 | 数据库记录正确 | PRD AC-6 |
| MKC-TC-S4-2-006 | Functional | Integration | P0 | 实体存储到 resource_entities | 提供 resource_id 与实体 | 调用 entity_repository.upsert 后查询 | 数据库记录正确 | PRD AC-6 |
| MKC-TC-S4-2-007 | Functional | Integration | P1 | 资源处理完成后异步触发抽取 | 资源处理任务完成 | 检查 Celery 任务是否触发 | extract_tags_task 被调用 | PRD AC-1 |
| MKC-TC-S4-2-008 | Functional | Integration | P1 | 内部接口触发抽取 | X-Internal-Key 有效 | POST /ai/v1/resources/{id}/extract-tags | 返回标签与实体 | PRD AC-7 |
| MKC-TC-S4-2-009 | Functional | Integration | P1 | Gateway 查询标签接口 | Bearer JWT 有效 | GET /api/v1/resources/{id}/tags | 返回标签与实体列表 | PRD AC-7 |
| MKC-TC-S4-2-010 | Functional | Unit | P1 | 实体类型非法被过滤 | LLM 返回 UNKNOWN 类型 | 调用 llm_provider._parse | 仅保留合法类型 | PRD AC-3 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-2-011 | Security | Integration | P0 | 内部接口 X-Internal-Key 认证 | 缺少或错误 Key | POST extract-tags | 返回 401 UNAUTHORIZED | PRD AC-7 |
| MKC-TC-S4-2-012 | Security | Integration | P0 | Gateway 接口 Bearer JWT 认证 | 缺少或无效 JWT | GET /api/v1/resources/{id}/tags | 返回 401 | PRD AC-7 |
| MKC-TC-S4-2-013 | Security | Static | P1 | 无硬编码 LLM API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |
| MKC-TC-S4-2-014 | Security | Integration | P1 | LLM 调用失败不暴露 Key | 模拟错误 | 查看日志与响应 | 无 Key 泄露 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-2-015 | Negative | Unit | P0 | LLM 非法 JSON 重试 | Mock LLM 返回非法 JSON | 调用 llm_provider.extract | 重试 3 次后降级规则抽取 | PRD AC-8 |
| MKC-TC-S4-2-016 | Negative | Unit | P0 | LLM 失败降级规则抽取 | Mock LLM 抛异常 | 调用 extraction_service.extract | source=rule，fallback=true | PRD AC-8 |
| MKC-TC-S4-2-017 | Negative | Unit | P0 | 空内容兜底返回空结果 | content 为空字符串 | 调用 extraction_service.extract | tags 与 entities 为空，fallback=true | PRD AC-8 |
| MKC-TC-S4-2-018 | Negative | Unit | P1 | LLM 超时降级规则抽取 | Mock LLM 超时 | 调用 extraction_service.extract | 降级为规则抽取 | PRD AC-8 |
| MKC-TC-S4-2-019 | Negative | Integration | P1 | 资源不存在返回 404 | resource_id 无效 | POST extract-tags | 返回 404 RESOURCE_NOT_FOUND | TECH 7 |
| MKC-TC-S4-2-020 | Reliability | Unit | P1 | 标签数量不足保留实际结果 | LLM 返回 3 个标签 | 调用 tag_normalizer.normalize | 返回 3 个标签不补全 | PRD AC-2 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-2-021 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-9 |
| MKC-TC-S4-2-022 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |
| MKC-TC-S4-2-023 | Security | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 secret | 仅环境变量 | 安全基线 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-2-024 | Performance | Integration | P1 | 大文本分批抽取 | 文本超过 max_chars | 调用 llm_provider.extract | 截断后抽取不报错 | TECH 6.1 |
| MKC-TC-S4-2-025 | Compatibility | Integration | P2 | 资源卡片展示标签与实体 | 抽取已完成 | GET /api/v1/resources/{id}/tags | 返回结构供 S4-3 卡片渲染 | PRD Web 适配 |
| MKC-TC-S4-2-026 | Compatibility | E2E | P2 | 音频与 PDF 资源均可抽取 | 提供两种 source_type | 分别调用 extract-tags | 均返回标签与实体 | PRD AC-1 |

## 4. 测试执行清单

- [ ] LLM 标签抽取（5-10 个）
- [ ] LLM 实体抽取（PERSON/ORG/DATE/LOC/GPE/MISC）
- [ ] 标签去重与归一化
- [ ] LLM JSON mode 结构化输出
- [ ] resource_tags 存储
- [ ] resource_entities 存储
- [ ] 异步任务触发
- [ ] 内部接口 X-Internal-Key 认证
- [ ] Gateway 接口 Bearer JWT 认证
- [ ] LLM 非法 JSON 重试 + 降级
- [ ] LLM 失败降级规则抽取
- [ ] 空内容兜底
- [ ] 覆盖率 80%+
- [ ] ruff / mypy 通过
- [ ] 无硬编码密钥
- [ ] 大文本分批处理

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
