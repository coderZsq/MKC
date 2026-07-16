# PRD：[S5-6] 完善错误处理与降级策略

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S0-5_api_interface_design.md](./PRD_S0-5_api_interface_design.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-6 |
| **任务名称** | 完善错误处理与降级策略 |
| **所属史诗** | E11 可观测性 |
| **故事点** | 3 |
| **优先级** | Should |
| **依赖** | S1-S4 已完成主链路 |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为用户和开发者，我希望系统在超时、依赖不可用、模型失败、任务异常或客户端网络波动时能给出一致、可理解、可追踪的错误提示，并尽可能降级为可用结果，以便项目达到生产级演示稳定性。

---

## 验收标准（AC）

- [ ] **AC-1** Gateway 与 AI Service 使用统一错误响应结构，包含 `code`、`message`、`trace_id`、`retryable`
- [ ] **AC-2** 对上传、异步任务、检索、Embedding、LLM、SSE 分别定义超时和重试策略
- [ ] **AC-3** LLM 或 Web Search 失败时支持基于已有检索上下文降级回答或返回友好提示
- [ ] **AC-4** 客户端展示用户友好错误，不暴露堆栈、SQL、密钥或内部路径
- [ ] **AC-5** 重试仅用于幂等或明确安全的操作，避免重复写入或重复扣费
- [ ] **AC-6** 错误日志携带 trace_id、error code 与上下文 ID，敏感内容脱敏
- [ ] **AC-7** 提供错误码文档与排障 runbook
- [ ] **AC-8** 单元/集成/Widget 测试覆盖率 80%+

---

## 推荐目录结构

```text
gateway/
├── internal/errors/
│   ├── codes.go
│   └── response.go
ai-service/
├── app/errors/
│   ├── codes.py
│   └── handlers.py
client/
└── lib/core/error/
    ├── app_error.dart
    └── error_mapper.dart
docs/runbooks/
└── error_handling.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Gin | 1.x | Gateway 错误中间件 |
| pydantic | 2.x | AI Service 错误模型 |
| Dio | 5.x | Flutter 网络错误拦截 |
| Riverpod | 2.x | UI 错误状态管理 |

---

## 技术要点

- 错误码格式建议：`DOMAIN_REASON`，如 `LLM_TIMEOUT`、`TASK_NOT_FOUND`。
- HTTP 状态与业务错误码一一映射，前端只根据错误码决定展示与重试按钮。
- SSE 错误使用事件 `event: error`，payload 沿用统一结构。
- 降级策略按“可回答但不完整”“暂不可用”“需用户重试”三类处理。
- 错误码文档必须说明触发条件、用户文案、开发排查路径。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 历史接口错误结构不一致 | 前端处理复杂 | 网关统一包装，逐接口迁移 |
| 过度重试 | 延迟和成本增加 | 明确 retryable 与最大次数 |
| 降级掩盖真实故障 | 排查困难 | 降级响应仍记录 error code 与 trace_id |

---

## Web 端适配

Flutter Web 需要特别处理浏览器网络中断、SSE 断流、文件选择失败与跨域错误。错误提示应适配窄屏，不遮挡当前回答内容。

---

## 备注

- 本卡应优先覆盖 Demo 主链路中的高频错误。
- 与 S5-3、S5-4 联动，错误响应中的 trace_id 与监控指标保持一致。
