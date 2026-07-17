# S5-4 Prometheus and Grafana Monitoring

## Local Metrics

Gateway exposes Prometheus metrics on:

```bash
curl http://localhost:8080/metrics
```

AI Service exposes Prometheus metrics on:

```bash
curl http://localhost:5000/metrics
```

Both endpoints use low-cardinality labels only. Do not add raw questions, file names, JWTs, API keys, or user-provided text as labels.

## Prometheus

Use `infra/observability/prometheus/scrape-config.yaml` as the local scrape config:

```bash
prometheus --config.file=infra/observability/prometheus/scrape-config.yaml
```

The config scrapes:

- `gateway:8080`
- `ai-service:5000`

In Kubernetes, keep `/metrics` internal. Do not expose metrics through public Ingress.

## Grafana

Import dashboard JSON files from:

- `infra/observability/grafana/dashboards/mkc-overview.json`
- `infra/observability/grafana/dashboards/mkc-ai-service.json`

The overview dashboard covers QPS, P95/P99 latency, and 5xx error rate. The AI dashboard covers LLM request volume, tokens, failure rate, retrieval requests, and task duration.

## Troubleshooting

- QPS drops to zero: check Prometheus targets and service DNS.
- P95/P99 spikes: inspect Gateway and AI latency panels separately.
- 5xx rate rises: use logs with `trace_id` from S5-3 to inspect failing requests.
- AI failures rise: compare `mkc_ai_llm_requests_total{status="error"}` and retrieval error counters.

