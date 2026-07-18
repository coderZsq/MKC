# Development Guide

This guide keeps the local workflow close to CI while still allowing fast iteration on one module at a time.

## Prerequisites

| Tool | Purpose |
|---|---|
| Docker Desktop with Kubernetes | Local MySQL, Redis, MinIO, Milvus, Jaeger |
| `kubectl` | Apply manifests and inspect pods |
| `envsubst` | Render local Secret templates |
| Go 1.22+ | Gateway development |
| Python 3.11+ | AI Service development |
| Flutter 3.22+ | Client development |
| Node.js 20+ | Documentation lint and link checks through `npx` |

## First-Time Setup

```bash
git clone https://github.com/coderZsq/MKC.git
cd MKC

cd ai-service
python -m venv .venv
source .venv/bin/activate
make install
cp config/.env.example .env
cd ..

cd client
flutter pub get
cd ..
```

The Gateway has no vendored dependencies; Go downloads modules on first build or test.

## Start Dependencies

```bash
export MYSQL_ROOT_PASSWORD=dev-root
export MYSQL_PASSWORD=dev-mkc
export REDIS_PASSWORD=dev-redis
export MINIO_ROOT_PASSWORD=dev-minio

./infra/scripts/local-up.sh
./infra/scripts/port-forward.sh
```

Run `port-forward.sh` in a long-lived terminal. The application services use localhost ports from that script.

## Start All Application Processes

```bash
./scripts/local-dev-up.sh
```

Defaults:

| Setting | Value |
|---|---|
| AI Service | `http://localhost:5001` |
| Gateway | `http://localhost:8080` |
| Client device | `chrome` |
| Client API | `http://localhost:8080/api/v1` |
| Logs | `.mkc-dev/logs/` |

Override examples:

```bash
CLIENT_DEVICE=macos AI_PORT=5001 GATEWAY_PORT=8080 ./scripts/local-dev-up.sh
```

Stop application processes:

```bash
./scripts/local-dev-down.sh
```

## Module Commands

Gateway:

```bash
cd gateway
go test ./...
go vet ./...
go build ./cmd/server
```

AI Service:

```bash
cd ai-service
DEBUG=true .venv/bin/python -m ruff check .
DEBUG=true .venv/bin/python -m black --check .
DEBUG=true .venv/bin/python -m mypy app
INTERNAL_API_KEY=test-internal-key LLM_PROVIDER=mock LLM_MODEL=glm-4-flash LLM_API_KEY= KIMI_API_KEY=test-key DEBUG=true .venv/bin/python -m pytest -q
```

Client:

```bash
cd client
flutter analyze
flutter test
flutter run -d chrome \
  --dart-define=BASE_URL=http://localhost:8080/api/v1 \
  --dart-define=STORAGE_HOST=localhost
```

Docs:

```bash
npx --yes markdownlint-cli README.md 'docs/**/*.md'
npx --yes markdown-link-check README.md --config .markdown-link-check.json
find docs -name '*.md' -print0 | xargs -0 -n1 npx --yes markdown-link-check --config .markdown-link-check.json
```

## Environment Variables

Gateway config starts from [gateway/config/config.example.yaml](../gateway/config/config.example.yaml). Values can be overridden with `APP_`-prefixed environment variables, for example `APP_SERVER_PORT=9090`.

AI Service config starts from [ai-service/config/.env.example](../ai-service/config/.env.example). Keep local `.env` files untracked.

Common local values:

| Variable | Local Value |
|---|---|
| `INTERNAL_API_KEY` | `dev-internal-key` |
| `APP_AI_SERVICE_INTERNAL_KEY` | `dev-internal-key` |
| `REDIS_URL` | `redis://:dev-redis@localhost:6379/0` |
| `CELERY_BROKER_URL` | `redis://:dev-redis@localhost:6379/1` |
| `MINIO_ENDPOINT` | `localhost:9000` |
| `EMBEDDING_PROVIDER` | `mock` or `ollama` |
| `LLM_PROVIDER` | `mock` or `ollama` |

When using Ollama embeddings, keep `EMBEDDING_DIMENSIONS` and `VECTOR_STORE_DIMENSIONS` aligned. If you change dimensions, drop the local vector collection or delete the local Milvus database before re-embedding.

## Branch and PR Workflow

- Branch from `main`.
- Keep each feature branch scoped to one sprint card.
- Do not commit `.env`, generated `secret.yaml`, local databases, logs, or `.mkc-dev/`.
- Run the relevant module checks before opening a PR.
- Include covered test-case IDs in the PR body when a sprint card has a test-case document.

## Useful Links

- [Architecture](ARCHITECTURE.md)
- [Deployment](DEPLOYMENT.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [API Design](api/api-design.md)
- [OpenAPI](api/openapi.yaml)
