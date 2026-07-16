# PRD：[S5-4] 接入 Prometheus + Grafana 监控

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S0-2_local_k8s_manifests.md](./PRD_S0-2_local_k8s_manifests.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-4 |
| **任务名称** | 接入 Prometheus + Grafana 监控 |
| **所属史诗** | E11 可观测性 |
| **故事点** | 3 |
| **优先级** | Could |
| **依赖** | S0-2 本地 K8s manifests |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为开发者，我希望 Gateway、AI Service 与关键异步任务暴露 Prometheus 指标，并提供 Grafana 看板展示 QPS、Latency、错误率、任务耗时和 LLM 调用情况，以便快速判断系统是否健康并定位性能瓶颈。

---

## 验收标准（AC）

- [ ] **AC-1** Gateway 暴露 `/metrics`，包含 HTTP 请求数、延迟直方图、错误数
- [ ] **AC-2** AI Service 暴露 `/metrics`，包含检索、Embedding、LLM、任务处理指标
- [ ] **AC-3** Prometheus 可通过 ServiceMonitor 或 scrape config 采集两个服务
- [ ] **AC-4** Grafana 提供系统总览看板：QPS、P95/P99 latency、5xx 错误率
- [ ] **AC-5** Grafana 提供 AI 看板：LLM 调用量、Token、失败率、任务队列耗时
- [ ] **AC-6** 指标标签控制基数，不包含原始问题、文件名、JWT 或密钥
- [ ] **AC-7** 提供本地与 K8s 部署说明
- [ ] **AC-8** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```text
gateway/
└── internal/observability/metrics/
ai-service/
└── app/observability/metrics.py
infra/
└── observability/
    ├── prometheus/
    │   └── scrape-config.yaml
    └── grafana/
        └── dashboards/
            ├── mkc-overview.json
            └── mkc-ai-service.json
docs/runbooks/
└── monitoring.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| prometheus/client_golang | 1.x | Gateway metrics |
| prometheus-client | 0.x | AI Service metrics |
| Prometheus | 2.x | 指标采集 |
| Grafana | 10.x+ | 看板展示 |

---

## 技术要点

- HTTP latency 使用 histogram，bucket 覆盖 50ms 到 30s。
- AI 指标按 provider、model、operation、status 等低基数标签聚合。
- `/metrics` 可在内网暴露，公网环境需通过网络策略或认证保护。
- Grafana dashboard JSON 纳入版本管理，避免手工配置丢失。
- 监控采集失败不影响业务请求。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 标签基数失控 | Prometheus 内存增长 | 标签白名单，禁止动态用户输入 |
| 看板依赖本地手工配置 | 部署不可复现 | dashboard JSON 入库并提供导入脚本 |
| 监控端点暴露公网 | 信息泄露 | K8s NetworkPolicy / Ingress 限制 |

---

## Web 端适配

本任务不涉及 Web 端特殊适配。用户可通过 Grafana Web UI 查看内部监控，但客户端无需改动。

---

## 备注

- 本卡支撑 Sprint 5 Demo 检查项中的 QPS、Latency、错误率看板。
- 后续告警规则可独立成卡。
