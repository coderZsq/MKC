# Deployment Guide

MKC currently supports a local Kubernetes dependency stack plus host-run app services. The repository also contains the building blocks for Kubernetes deployment, but production deployment requires image publishing, hardened secrets, ingress configuration, and environment-specific manifests.

## Deployment Modes

| Mode | Status | Use Case |
|---|---|---|
| Local dependencies + host app processes | Supported | Daily development |
| Local Kubernetes dependencies only | Supported | Testing infrastructure manifests |
| Full Kubernetes app deployment | Supported through Kustomize | Gateway, AI Service, worker, Client, and dependencies |
| Production Kubernetes | Template provided | Domain, TLS, resources, smoke, and rollback |

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
├── base/
├── overlays/
│   ├── local/
│   └── prod/
├── namespaces/
├── nginx-ingress/
├── mysql/
├── redis/
├── minio/
├── milvus/
├── jaeger/
└── gateway/
```

The S5-8 deployment entrypoint is Kustomize:

```bash
kubectl kustomize infra/k8s/overlays/local
kubectl kustomize infra/k8s/overlays/prod
```

`infra/k8s/base` defines Gateway, AI Service, AI worker, Client, MySQL, Redis, MinIO, Milvus, internal services, persistence, probes, resources, and Ingress. `overlays/local` uses `mkc.local`; `overlays/prod` enables cert-manager TLS and immutable image tags.

Apply local manifests through the script instead of applying directories by hand:

```bash
./infra/scripts/local-up.sh
```

Apply full application overlays:

```bash
./scripts/deploy_k8s.sh local
./scripts/deploy_k8s.sh prod
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

## Domain and TLS

Production Ingress is defined in `infra/k8s/overlays/prod`. Before applying it:

1. Point the DNS record for the demo domain to the ingress load balancer.
2. Replace `MKC_DOMAIN=mkc.example.com` in `infra/k8s/overlays/prod/kustomization.yaml`.
3. Replace `ops@example.com` in `infra/k8s/overlays/prod/cluster-issuer.yaml`.
4. Confirm cert-manager is installed.

The Ingress includes SSE and upload annotations:

- `nginx.ingress.kubernetes.io/proxy-buffering: "off"`
- `nginx.ingress.kubernetes.io/proxy-read-timeout: "600"`
- `nginx.ingress.kubernetes.io/proxy-send-timeout: "600"`
- `nginx.ingress.kubernetes.io/proxy-body-size: "500m"`

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
- Prod overlay image tags are immutable and reviewed.
- Secrets are injected from a safe source.
- Gateway and AI Service health checks pass.
- Database migrations have been applied.
- Client build points to the public Gateway base URL.
- SSE works through ingress without buffering.
- Upload size limits are aligned across browser, Gateway, ingress, and object storage.
- Rollback image tags and database backup are available.

## Smoke Test

```bash
BASE_URL=https://mkc.example.com \
NAMESPACE=mkc \
./scripts/smoke_prod.sh
```

To include upload verification:

```bash
BASE_URL=https://mkc.example.com \
UPLOAD_FILE=/path/to/smoke.pdf \
./scripts/smoke_prod.sh
```

## Rollback

```bash
kubectl rollout undo deployment/gateway -n mkc
kubectl rollout undo deployment/ai-service -n mkc
kubectl rollout undo deployment/client -n mkc
kubectl rollout status deployment/gateway -n mkc --timeout=300s
```

For data-impacting releases, restore MySQL/MinIO/Milvus backups that match the release window.

## Related Docs

- [Architecture](ARCHITECTURE.md)
- [Development](DEVELOPMENT.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Infrastructure README](../infra/README.md)
- [S5-8 Kubernetes domain deployment TECH](tech/TECH_S5-8_k8s_domain_deployment.md)
- [Kubernetes domain deployment runbook](runbooks/k8s_domain_deployment.md)
