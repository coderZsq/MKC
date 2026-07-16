# S5-3 测试用例：接入 OpenTelemetry 链路追踪

## 1. 范围与目标

验证 Gateway 与 AI Service 的 trace 初始化、HTTP span、trace context 透传、业务 span、错误标记、日志 trace_id 和降级行为。

## 2. 测试环境

- Go 1.22+
- Python 3.11+
- OpenTelemetry SDK
- mock OTLP exporter / console exporter

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-3-001 | Functional | Integration | P0 | Gateway 请求创建 root span | tracing enabled | 调用任意 API | span 包含 method/path/status | PRD AC-1 |
| MKC-TC-S5-3-002 | Functional | Integration | P0 | AI Service 延续 trace context | Gateway 调 AI | 检查 span trace_id | 两服务 trace_id 一致 | PRD AC-2 |
| MKC-TC-S5-3-003 | Functional | Unit | P1 | 关键业务 span 创建 | mock RAG 流程 | 执行检索/LLM | 生成对应 span | PRD AC-3 |
| MKC-TC-S5-3-004 | Functional | Unit | P1 | noop exporter 可用 | 未配置 endpoint | 启动服务 | 不报错并使用 noop | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-3-005 | Security | Static | P0 | span 不记录敏感内容 | span 已生成 | 检查 attributes | 无 JWT/API Key/问题全文 | PRD AC-5 |
| MKC-TC-S5-3-006 | Security | Unit | P1 | trace_id 可写入日志 | 请求执行 | 检查日志字段 | 日志包含 trace_id | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-3-007 | Negative | Integration | P0 | 业务异常标记错误 span | mock handler 抛错 | 调用 API | span status=ERROR | PRD AC-5 |
| MKC-TC-S5-3-008 | Negative | Unit | P1 | collector 不可用不影响业务 | endpoint 不可达 | 调用 API | API 正常返回或业务错误 | PRD AC-7 |
| MKC-TC-S5-3-009 | Negative | Unit | P2 | 非法 traceparent 可降级 | 传非法 header | 调用 AI Service | 创建新 trace 不崩溃 | PRD AC-7 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-3-010 | Functional | Static | P1 | Go/Python 测试覆盖率 80%+ | 测试存在 | 运行测试覆盖率 | coverage >= 80% | PRD AC-8 |
| MKC-TC-S5-3-011 | Functional | Static | P1 | go test/ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] 跨服务 trace_id 一致
- [ ] 错误 span 标记正确
- [ ] 敏感字段未写入 span
- [ ] 覆盖率 80%+
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
