# PRD：[S5-5] 接入 LangSmith / Langfuse

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S3-5_glm4_kimi_llm.md](./PRD_S3-5_glm4_kimi_llm.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-5 |
| **任务名称** | 接入 LangSmith / Langfuse |
| **所属史诗** | E11 可观测性 |
| **故事点** | 2 |
| **优先级** | Could |
| **依赖** | S3-5 智谱 GLM-4 / Kimi 生成答案 |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为开发者，我希望对 LLM 调用、Prompt、模型响应、Token 用量与失败原因进行可选观测，以便调试问答质量、分析成本并支持后续 Prompt 优化。本任务支持 LangSmith 或 Langfuse 作为 provider，默认关闭，缺少配置时不影响业务与 CI。

---

## 验收标准（AC）

- [ ] **AC-1** LLM 调用封装层支持可插拔 tracing callback
- [ ] **AC-2** 支持 LangSmith 与 Langfuse 至少一种 provider，配置可切换
- [ ] **AC-3** 记录 prompt template version、model、latency、token、status 与 trace_id
- [ ] **AC-4** 对用户问题、文档片段与模型响应执行脱敏或截断策略
- [ ] **AC-5** provider 不可用时降级为 noop observer，不影响问答
- [ ] **AC-6** 提供本地启用说明与环境变量清单
- [ ] **AC-7** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── app/llm/
│   ├── observer.py
│   └── llm_client.py
├── app/observability/llm/
│   ├── langfuse_observer.py
│   ├── langsmith_observer.py
│   └── noop_observer.py
└── tests/unit/test_llm_observer.py
docs/runbooks/
└── llm_observability.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| langfuse | 2.x | LLM 调用观测 |
| langsmith | 0.x | LangChain/LangGraph 调用观测 |
| pydantic | 2.x | 配置校验 |

---

## 技术要点

- 通过 `LLM_OBSERVABILITY_PROVIDER=none/langfuse/langsmith` 控制启用状态。
- 所有 observer 实现统一接口：`start_trace`、`record_generation`、`record_error`、`flush`。
- prompt 和 completion 默认截断，敏感字段通过规则替换为 `[REDACTED]`。
- 业务请求只等待本地记录完成，远端发送失败走异步失败日志。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 第三方平台不可用 | 调试数据缺失 | noop 降级，不影响主流程 |
| Prompt 或用户内容外泄 | 安全风险 | 默认关闭、脱敏、截断与环境分级 |
| SDK 与现有链路冲突 | 问答异常 | 封装在 LLMClient 边界，保留 provider 开关 |

---

## Web 端适配

本任务不涉及 Web 端特殊适配。可在错误响应中复用后端 trace_id 便于定位 LLM 调用。

---

## 备注

- S5-3 的 OpenTelemetry trace_id 应写入 LLM 观测元数据。
- 本卡优先满足调试与复盘，不要求公开运营看板。
