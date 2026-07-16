# S5-6 测试用例：完善错误处理与降级策略

## 1. 范围与目标

验证 Gateway、AI Service、Flutter 客户端统一错误结构、错误码映射、超时重试、降级策略、日志 trace_id 和 Web 端错误展示。

## 2. 测试环境

- Go 1.22+
- Python 3.11+
- Flutter 3.22+
- Dio / Riverpod
- pytest / go test / flutter test

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-6-001 | Functional | Integration | P0 | Gateway 返回统一错误结构 | 构造 404 | 调用 API | 返回 code/message/trace_id/retryable | PRD AC-1 |
| MKC-TC-S5-6-002 | Functional | Unit | P0 | AI Service 异常映射统一 | mock LLM timeout | 调用 handler | 返回 LLM_TIMEOUT | PRD AC-1 |
| MKC-TC-S5-6-003 | Functional | Unit | P1 | 超时配置生效 | 配置 timeout | 调用依赖 | 超时按配置触发 | PRD AC-2 |
| MKC-TC-S5-6-004 | Functional | Integration | P1 | LLM 失败可降级提示 | mock LLM 失败 | 发起问答 | 返回友好提示或已有上下文答案 | PRD AC-3 |
| MKC-TC-S5-6-005 | Functional | Widget | P0 | 客户端展示友好错误 | mock Dio error | 渲染页面 | 无堆栈，显示用户文案 | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-6-006 | Security | Static | P0 | 错误响应不含敏感信息 | 触发异常 | 检查 response/log | 无 SQL/密钥/内部路径 | PRD AC-4 |
| MKC-TC-S5-6-007 | Security | Unit | P0 | 非幂等操作不自动重试 | 上传写入接口 | 模拟失败 | 不重复写入 | PRD AC-5 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-6-008 | Negative | Integration | P0 | SSE 错误事件格式正确 | mock stream error | 建立 SSE | 收到 event:error 统一 payload | PRD AC-1 |
| MKC-TC-S5-6-009 | Negative | Unit | P1 | 依赖不可用返回 503 | mock Redis/Milvus down | 调用接口 | 返回 DEPENDENCY_UNAVAILABLE | TECH 7 |
| MKC-TC-S5-6-010 | Negative | Unit | P1 | 日志包含 trace_id | 触发错误 | 检查日志 | 包含 trace_id/error code | PRD AC-6 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-6-011 | Functional | Static | P1 | 覆盖率 80%+ | 测试存在 | 运行覆盖率 | coverage >= 80% | PRD AC-8 |
| MKC-TC-S5-6-012 | Functional | Static | P1 | go test/pytest/flutter analyze 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-6-013 | Compatibility | Widget | P1 | Web 网络断开提示 | Flutter Web | mock network error | 显示重试入口 | PRD Web 端适配 |
| MKC-TC-S5-6-014 | Compatibility | Integration | P1 | Web SSE 断流提示 | Flutter Web | 中断 SSE | UI 显示连接中断 | PRD Web 端适配 |

## 4. 测试执行清单

- [ ] 统一错误结构通过
- [ ] 降级策略通过
- [ ] Web 错误展示通过
- [ ] 覆盖率 80%+
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
