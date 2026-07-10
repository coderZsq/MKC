# S3-5 测试用例：接入智谱 GLM-4 / Kimi 生成答案

## 1. 范围与目标

验证 AI Service LLM 模块：统一接口、智谱 GLM-4 与 Kimi provider、同步/流式生成、重试、超时、错误处理与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- zhipuai 2.x
- openai 1.30+
- tenacity 8.x
- pytest, pytest-cov
- mock provider（本地开发）

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-5-001 | Functional | Unit | P0 | 同步生成返回完整答案 | 配置 provider=zhipuai | 调用 LLMClient.complete | 返回 LLMResponse | PRD AC-1 |
| MKC-TC-S3-5-002 | Functional | Unit | P0 | 流式生成逐字返回 | 配置 provider=zhipuai | 调用 LLMClient.stream_complete | 返回增量 chunk | PRD AC-3 |
| MKC-TC-S3-5-003 | Functional | Integration | P0 | SSE 流式接口格式正确 | 启动服务 | POST /ai/v1/llm/stream | 返回 SSE 事件流 | PRD AC-3 |
| MKC-TC-S3-5-004 | Functional | Unit | P1 | 配置切换至 Kimi | 配置 provider=kimi | 调用 complete | 使用 Kimi provider | PRD AC-2 |
| MKC-TC-S3-5-005 | Functional | Unit | P1 | 温度与 max_tokens 生效 | 配置参数 | 调用 complete | 请求体包含对应参数 | PRD AC-4 |
| MKC-TC-S3-5-006 | Functional | Unit | P2 | 返回 usage 信息 | 正常生成 | 调用 complete | 返回包含 usage 字段 | PRD AC-1 |
| MKC-TC-S3-5-007 | Functional | Integration | P2 | mock provider 本地开发可用 | 配置 provider=mock | 调用 complete | 返回固定文本 | PRD AC-7 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-5-008 | Security | Integration | P0 | 缺少内部 Key 拒绝访问 | 请求头无 Key | POST /ai/v1/llm/stream | 返回 401 | TECH 3 |
| MKC-TC-S3-5-009 | Security | Static | P1 | 无硬编码 API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-5-010 | Negative | Unit | P0 | API Key 缺失启动失败 | 未设置 ZHIPU_API_KEY | 启动服务 | 报错拒绝启动 | PRD AC-6 |
| MKC-TC-S3-5-011 | Negative | Unit | P1 | 主模型失败切换备选 | 配置 fallback model | 调用 complete | 使用备选模型 | PRD 降级策略 |
| MKC-TC-S3-5-012 | Negative | Unit | P1 | 流式中断返回已生成内容 | 模拟流中断 | 调用 stream_complete | 返回已生成内容并标记错误 | PRD 降级策略 |
| MKC-TC-S3-5-013 | Negative | Unit | P1 | 超时返回 504 | 模拟 LLM 超时 | 调用 complete | 返回 LLM_TIMEOUT | PRD AC-4 |
| MKC-TC-S3-5-014 | Negative | Unit | P1 | 重试 3 次后失败 | mock 连续失败 | 调用 complete | 第 3 次失败后抛异常 | PRD AC-5 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-5-015 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-8 |
| MKC-TC-S3-5-016 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-5-017 | Compatibility | Unit | P2 | 智谱与 Kimi provider 接口一致 | 同一段请求 | 分别调用 | 返回相同结构 | PRD AC-2 |
| MKC-TC-S3-5-018 | Performance | Integration | P2 | 流式首字延迟 < 2s | 使用 mock | POST /ai/v1/llm/stream | 首字延迟 < 2s | 性能基线 |

## 4. 测试执行清单

- [ ] 同步生成与流式生成
- [ ] 智谱与 Kimi provider
- [ ] SSE 格式与事件类型
- [ ] 重试与超时
- [ ] 模型降级
- [ ] 认证与权限
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
