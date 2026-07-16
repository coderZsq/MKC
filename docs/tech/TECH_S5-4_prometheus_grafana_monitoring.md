# 技术文档：[S5-4] 接入 Prometheus + Grafana 监控

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：后端/AI 工程师
> 关联 PRD：[../prd/PRD_S5-4_prometheus_grafana_monitoring.md](../prd/PRD_S5-4_prometheus_grafana_monitoring.md)

---

## 1. 文档目标

定义 Gateway、AI Service 的 Prometheus 指标、采集配置、Grafana dashboard 和监控测试策略。

---

## 2. 技术栈

- Go 1.22+, Gin
- Python 3.11+, Flask/FastAPI
- prometheus/client_golang
- prometheus-client
- Prometheus 2.x
- Grafana 10.x+

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/metrics` | 内网 | Prometheus 指标 |
| GET | `/healthz` | 无 | 存活检查 |
| GET | `/readyz` | 无 | 就绪检查 |

核心指标：

```text
mkc_gateway_http_requests_total{method,path,status}
mkc_gateway_http_request_duration_seconds_bucket{method,path}
mkc_ai_llm_requests_total{provider,model,status}
mkc_ai_task_duration_seconds_bucket{task_type,status}
```

---

## 4. 配置

```yaml
observability:
  metrics:
    enabled: true
    path: /metrics
    namespace: mkc
```

Prometheus scrape：

```yaml
scrape_configs:
  - job_name: mkc-gateway
    static_configs:
      - targets: ["gateway:8080"]
  - job_name: mkc-ai-service
    static_configs:
      - targets: ["ai-service:8000"]
```

---

## 5. 模块设计

- Gateway metrics middleware：统计请求数、延迟、错误率。
- AI metrics registry：记录检索、Embedding、LLM、任务队列指标。
- dashboard provisioning：Grafana JSON 入库。
- runbook：解释指标含义、常见异常和排查路径。

---

## 6. 关键代码实现

```go
httpRequests := promauto.NewCounterVec(
    prometheus.CounterOpts{Name: "mkc_gateway_http_requests_total"},
    []string{"method", "path", "status"},
)
```

```python
LLM_REQUESTS = Counter(
    "mkc_ai_llm_requests_total",
    "LLM request count",
    ["provider", "model", "status"],
)
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| metrics 未启用 | 404 | METRICS_DISABLED | 指标端点未启用 |
| metrics registry 冲突 | 500 | METRICS_REGISTRY_ERROR | 指标注册失败 |
| dashboard 导入失败 | N/A | GRAFANA_IMPORT_FAILED | Grafana 看板导入失败 |

---

## 8. Web 端适配要点

客户端无需改动。若 Web Demo 需要展示系统状态，应通过后端聚合接口而不是直接暴露 Prometheus。

---

## 9. 测试策略

- 单元测试：指标 label、计数、histogram bucket。
- 集成测试：`/metrics` 返回 Prometheus 文本格式。
- 静态检查：禁止高基数标签和敏感字段。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] 测试覆盖率 80%+
- [ ] Grafana dashboard JSON 已提交
