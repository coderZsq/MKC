# 技术文档：[S5-3] 接入 OpenTelemetry 链路追踪

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：后端/AI 工程师
> 关联 PRD：[../prd/PRD_S5-3_opentelemetry_tracing.md](../prd/PRD_S5-3_opentelemetry_tracing.md)

---

## 1. 文档目标

定义 Gateway 与 AI Service 的 OpenTelemetry 初始化、HTTP 中间件、跨服务 trace context 透传、业务 span 与错误记录规范。

---

## 2. 技术栈

- Go 1.22+, Gin
- Python 3.11+, Flask/FastAPI
- OpenTelemetry SDK
- OTLP exporter
- OpenTelemetry Collector

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| Header | `traceparent` | 无 | W3C Trace Context |
| Header | `tracestate` | 无 | 可选 trace 状态 |
| GET | `/healthz` | 无 | 健康检查，不强依赖 tracing |

错误响应应包含：

```json
{
  "code": "LLM_TIMEOUT",
  "message": "模型调用超时，请稍后重试",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

---

## 4. 配置

```yaml
observability:
  tracing:
    enabled: true
    service_name: mkc-gateway
    exporter: otlp
    endpoint: http://otel-collector:4318
    sample_ratio: 0.1
```

---

## 5. 模块设计

- Gateway `tracing.InitTracer`：初始化 exporter、resource 与 sampler。
- Gateway `TracingMiddleware`：创建 HTTP root span，注入 trace_id 到 context。
- AI Service `init_tracing`：配置 Flask/FastAPI instrumentation。
- `SpanHelper`：封装业务 span 和错误标记。
- HTTP client wrapper：注入 `traceparent` 到 AI Service 请求。

---

## 6. 关键代码实现

```go
func TracingMiddleware(tracer trace.Tracer) gin.HandlerFunc {
    return func(c *gin.Context) {
        ctx, span := tracer.Start(c.Request.Context(), c.FullPath())
        defer span.End()
        c.Request = c.Request.WithContext(ctx)
        c.Writer.Header().Set("X-Trace-Id", span.SpanContext().TraceID().String())
        c.Next()
    }
}
```

```python
with tracer.start_as_current_span("rag.retrieve") as span:
    span.set_attribute("resource.count", len(resource_ids))
    span.set_attribute("retrieval.top_k", top_k)
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| exporter 初始化失败 | N/A | TRACE_EXPORTER_INIT_FAILED | 链路追踪初始化失败，已降级 |
| trace context 解析失败 | N/A | TRACE_CONTEXT_INVALID | Trace 上下文非法，已重新创建 |
| collector 不可用 | N/A | TRACE_EXPORT_FAILED | Trace 上报失败 |

---

## 8. Web 端适配要点

Web 端读取响应头 `X-Trace-Id` 并在错误提示或反馈日志中保留，不要求浏览器端接入 OTel。

---

## 9. 测试策略

- 单元测试：middleware 注入 trace_id、错误 span 标记。
- 集成测试：Gateway 调 AI Service 时透传 `traceparent`。
- 静态检查：禁止 span attribute 包含原始 JWT、问题全文、密钥。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
