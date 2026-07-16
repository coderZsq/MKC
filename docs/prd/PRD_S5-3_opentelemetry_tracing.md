# PRD：[S5-3] 接入 OpenTelemetry 链路追踪

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S0-7_go_gateway_skeleton.md](./PRD_S0-7_go_gateway_skeleton.md)、[PRD_S0-8_python_ai_service_skeleton.md](./PRD_S0-8_python_ai_service_skeleton.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-3 |
| **任务名称** | 接入 OpenTelemetry 链路追踪 |
| **所属史诗** | E11 可观测性 |
| **故事点** | 3 |
| **优先级** | Could |
| **依赖** | S0-7 Go Gateway 骨架、S0-8 Python AI Service 骨架 |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为开发者，我希望 Gateway 与 AI Service 支持 OpenTelemetry Trace，并在跨服务调用时透传 `traceparent`，以便排查上传、异步任务、检索、LLM 调用和回答生成中的延迟与错误。本任务要求追踪能力可配置开启，默认不阻塞业务链路。

---

## 验收标准（AC）

- [ ] **AC-1** Gateway HTTP 请求自动创建 root span，并记录 method、path、status、latency
- [ ] **AC-2** AI Service 接收并延续 Gateway 的 trace context
- [ ] **AC-3** 上传、任务状态、检索、Embedding、LLM、SSE 输出等关键步骤具备业务 span
- [ ] **AC-4** 支持 OTLP HTTP/gRPC exporter 配置，未配置时可使用 console/noop exporter
- [ ] **AC-5** 错误 span 标记 `StatusCode.ERROR` 并记录脱敏后的 error code
- [ ] **AC-6** 日志输出包含 `trace_id`，便于从日志跳转到 Trace
- [ ] **AC-7** 链路追踪失败不影响主流程
- [ ] **AC-8** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```text
gateway/
├── internal/observability/tracing/
│   ├── tracer.go
│   └── middleware.go
└── config/config.yaml
ai-service/
├── app/observability/tracing.py
└── config/ai.yaml
infra/
└── k8s/observability/otel-collector.yaml
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| go.opentelemetry.io/otel | 1.x | Gateway tracing |
| opentelemetry-sdk | 1.x | AI Service tracing |
| opentelemetry-instrumentation-flask | 0.x | Flask 自动埋点 |
| OpenTelemetry Collector | latest | Trace 收集与转发 |

---

## 技术要点

- 所有跨服务 HTTP 请求透传 W3C `traceparent` 和 `tracestate`。
- span name 使用低基数字段，例如 `GET /api/v1/resources/:id`。
- 禁止记录用户原始提问全文、文件正文、JWT、API Key。
- 关键业务属性包括 `user_id_hash`、`resource_id`、`task_id`、`model_provider`、`retrieval_top_k`。
- exporter 初始化失败时降级到 noop tracer 并输出 WARN 日志。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Trace 数据量过大 | 存储和成本上升 | 默认采样率 10%，支持环境变量调整 |
| 埋点泄露敏感内容 | 安全风险 | 属性白名单与日志脱敏 |
| collector 不可用 | 观测缺失 | exporter 失败不影响业务，保留本地日志 trace_id |

---

## Web 端适配

本任务不要求 Flutter Web 生成浏览器 Trace；Web 端只需在请求失败时保留后端返回的 `trace_id`，便于用户反馈问题时定位。

---

## 备注

- S5-4 监控与本卡互补：Trace 用于单请求定位，Metrics 用于趋势告警。
- 后续可扩展前端 RUM，但不纳入本卡范围。
