# 技术文档：[S5-6] 完善错误处理与降级策略

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：后端/前端/AI 工程师
> 关联 PRD：[../prd/PRD_S5-6_error_handling_fallback_strategy.md](../prd/PRD_S5-6_error_handling_fallback_strategy.md)

---

## 1. 文档目标

定义统一错误模型、错误码、HTTP 映射、重试与降级策略，以及 Flutter 展示规则。

---

## 2. 技术栈

- Go 1.22+, Gin
- Python 3.11+, Flask/FastAPI
- Flutter 3.22+, Riverpod, Dio
- Redis / Celery

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 任意 | `/api/v1/*` | Bearer JWT | 统一错误响应 |
| SSE | `/api/v1/chat/stream` | Bearer JWT | `event: error` 错误事件 |

错误响应：

```json
{
  "code": "LLM_TIMEOUT",
  "message": "模型响应超时，请稍后重试",
  "trace_id": "abc",
  "retryable": true,
  "details": {}
}
```

---

## 4. 配置

```yaml
resilience:
  upload_timeout_seconds: 60
  retrieval_timeout_seconds: 20
  llm_timeout_seconds: 60
  max_retries: 2
  retry_backoff_ms: 300
```

---

## 5. 模块设计

- Gateway `AppError`：统一错误类型与 HTTP status。
- AI Service `ErrorHandler`：转换模型、检索、任务异常。
- Client `ErrorMapper`：错误码映射用户文案与重试按钮。
- `RetryPolicy`：按操作声明是否可重试。
- runbook：错误码说明与排查路径。

---

## 6. 关键代码实现

```go
type ErrorResponse struct {
    Code      string         `json:"code"`
    Message   string         `json:"message"`
    TraceID   string         `json:"trace_id"`
    Retryable bool           `json:"retryable"`
    Details   map[string]any `json:"details,omitempty"`
}
```

```dart
AppError mapDioError(DioException error) {
  final code = error.response?.data['code'] ?? 'NETWORK_ERROR';
  return AppError(code: code, message: userMessageFor(code));
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 上传超限 | 413 | FILE_TOO_LARGE | 文件超过大小限制 |
| 任务不存在 | 404 | TASK_NOT_FOUND | 任务不存在或已过期 |
| 检索超时 | 504 | RETRIEVAL_TIMEOUT | 检索超时，请稍后重试 |
| LLM 超时 | 504 | LLM_TIMEOUT | 模型响应超时，请稍后重试 |
| 依赖不可用 | 503 | DEPENDENCY_UNAVAILABLE | 依赖服务暂不可用 |
| 未知错误 | 500 | INTERNAL_ERROR | 系统异常，请稍后重试 |

---

## 8. Web 端适配要点

Web 端需处理 CORS、SSE 断流、浏览器文件选择失败和网络离线，展示 trace_id 的短号或复制入口。

---

## 9. 测试策略

- 单元测试：错误码映射、retryable 判断、脱敏。
- 集成测试：Gateway/AI Service 异常转换。
- Widget 测试：Flutter 错误提示、重试按钮、SSE 错误事件。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] 测试覆盖率 80%+
- [ ] 错误码文档同步更新
