# Deployment Guide

MKC currently supports a local Kubernetes dependency stack plus host-run app services. The repository also contains the building blocks for Kubernetes deployment, but production deployment requires image publishing, hardened secrets, ingress configuration, and environment-specific manifests.

## Deployment Modes

| Mode | Status | Use Case |
|---|---|---|
| Local dependencies + host app processes | Supported | Daily development |
| Local Kubernetes dependencies only | Supported | Testing infrastructure manifests |
| Full Kubernetes app deployment | Partial | Gateway Service/Ingress exists; app Deployments need environment-specific completion |
| Production Kubernetes | Planned | S5-8 domain, TLS, and deployment hardening |

## Local Kubernetes

Start dependencies:

```bash
export MYSQL_ROOT_PASSWORD=dev-root
export MYSQL_PASSWORD=dev-mkc
export REDIS_PASSWORD=dev-redis
export MINIO_ROOT_PASSWORD=dev-minio

./infra/scripts/local-up.sh
```

Expose dependency ports to host processes:

```bash
./infra/scripts/port-forward.sh
```

Stop local infrastructure:

```bash
./infra/scripts/local-down.sh
```

## Docker Images

Gateway:

```bash
cd gateway
docker build -t mkc-gateway:latest .
```

AI Service:

```bash
cd ai-service
docker build -t mkc-ai-service:latest .
```

Client production build:

```bash
cd client
flutter build web \
  --dart-define=APP_ENV=prod \
  --dart-define=BASE_URL=https://api.example.com/api/v1 \
  --dart-define=STORAGE_HOST=storage.example.com
```

Use environment-specific image tags in real deployments, for example a short Git SHA. Do not deploy mutable `latest` tags outside local testing.

## Kubernetes Layout

```text
infra/k8s/
├── namespaces/
├── nginx-ingress/
├── mysql/
├── redis/
├── minio/
├── milvus/
├── jaeger/
└── gateway/
```

The current manifests deploy local infrastructure components and Gateway network resources. `infra/k8s/gateway/service.yaml` and `infra/k8s/gateway/ingress.yaml` assume a Gateway workload exists, but the environment-specific Deployment is intentionally left for the deployment sprint.

Apply local manifests through the script instead of applying directories by hand:

```bash
./infra/scripts/local-up.sh
```

## Secrets

Local templates are rendered with `envsubst`:

```bash
export MYSQL_ROOT_PASSWORD=dev-root
export MYSQL_PASSWORD=dev-mkc
export REDIS_PASSWORD=dev-redis
export MINIO_ROOT_PASSWORD=dev-minio
./infra/scripts/render-secrets.sh
```

Generated Secret files are ignored by Git. Production should use a secret manager or sealed/encrypted secrets. Required secret categories:

| Category | Examples |
|---|---|
| Gateway auth | JWT signing secret |
| Internal auth | Gateway-to-AI internal API key |
| Databases | MySQL and Redis passwords |
| Object storage | MinIO access and secret keys |
| Model providers | OpenAI, ZhipuAI, Kimi, Langfuse, or LangSmith keys |
| TLS | Certificate private keys when not managed by cert-manager |

## Runtime Environment

Gateway should receive configuration from `gateway/config/config.example.yaml` plus environment overrides. AI Service should receive values equivalent to `ai-service/config/.env.example`.

Production rules:

- Set Gin and Flask debug modes off.
- Expose Gateway and Client only through HTTPS.
- Keep AI Service, Redis, MySQL, MinIO, Milvus, metrics, and tracing endpoints private.
- Use read/write resource requests and limits for each workload.
- Run migrations before or during release with a rollback plan.
- Use object storage buckets and vector collections scoped by environment.

## Health and Readiness

Gateway:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/health
```

AI Service:

```bash
curl http://localhost:5001/api/v1/health
```

Kubernetes:

```bash
kubectl get pods -n mkc-dev
kubectl get svc -n mkc-dev
kubectl get ingress -n mkc-dev
```

## Observability

- Gateway metrics: `GET /metrics`
- AI Service metrics: `GET /metrics`
- Local traces: Jaeger at `localhost:16686` after port forwarding
- Grafana dashboards: [infra/observability/grafana/dashboards](../infra/observability/grafana/dashboards)
- Prometheus scrape config: [infra/observability/prometheus/scrape-config.yaml](../infra/observability/prometheus/scrape-config.yaml)

Do not expose metrics or tracing endpoints through public ingress.

## Release Checklist

- Images are built from the intended Git SHA.
- Secrets are injected from a safe source.
- Gateway and AI Service health checks pass.
- Database migrations have been applied.
- Client build points to the public Gateway base URL.
- SSE works through ingress without buffering.
- Upload size limits are aligned across browser, Gateway, ingress, and object storage.
- Rollback image tags and database backup are available.

## Related Docs

- [Architecture](ARCHITECTURE.md)
- [Development](DEVELOPMENT.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Infrastructure README](../infra/README.md)
- [S5-8 Kubernetes domain deployment TECH](tech/TECH_S5-8_k8s_domain_deployment.md)
