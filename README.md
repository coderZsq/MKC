# MKC - Multimedia AI Knowledge Companion

![CI - Gateway](https://github.com/coderZsq/mkc/actions/workflows/ci-gateway.yml/badge.svg)
![CI - AI Service](https://github.com/coderZsq/mkc/actions/workflows/ci-ai-service.yml/badge.svg)
![CI - Client](https://github.com/coderZsq/mkc/actions/workflows/ci-client.yml/badge.svg)

基于 Flutter + Go + Python 的多媒体 AI 知识库助手。

## 核心能力

- MP3 转录为 SRT 与文本
- PDF 解析为结构化文本
- 基于 RAG 的知识库问答
- 多轮 SSE 流式对话

## 技术栈

- 前端：Flutter + Clean Architecture + Riverpod
- 网关：Go + Gin + GORM + MySQL + Redis
- AI 服务：Python + Flask + Celery + LangGraph + LlamaIndex
- 基础设施：Kubernetes + nginx-ingress + MinIO + Milvus

## 快速开始

当前仓库最适合的本地开发方式是：

- 使用本地 Kubernetes 启动 MySQL / Redis / MinIO / Milvus / Jaeger 等基础设施
- 在宿主机直接启动 `ai-service`、`gateway`、`client` 三个开发进程

> 说明：`infra/k8s/gateway` 当前仅包含 Service / Ingress，尚未提供完整 Gateway Deployment。因此不建议直接用 Kubernetes 跑完整应用链路。

### 1. 启动本地基础设施

前置条件：

- Docker Desktop 已安装并启用 Kubernetes
- `kubectl` 可连接本地集群
- 已安装 `envsubst`，macOS 可通过 `brew install gettext` 安装

```bash
cd /Users/zhushuangquan/Downloads/MKC

export MYSQL_ROOT_PASSWORD=dev-root
export MYSQL_PASSWORD=dev-mkc
export REDIS_PASSWORD=dev-redis
export MINIO_ROOT_PASSWORD=dev-minio

./infra/scripts/local-up.sh
```

另开一个终端启动端口转发，并保持该终端运行：

```bash
cd /Users/zhushuangquan/Downloads/MKC
./infra/scripts/port-forward.sh
```

默认转发端口：

| 服务 | 本地地址 |
|---|---|
| MySQL | `localhost:3306` |
| Redis | `localhost:6379` |
| MinIO S3 | `localhost:9000` |
| MinIO Console | `localhost:9001` |
| Jaeger UI | `localhost:16686` |
| Milvus | `localhost:19530` |

### 2. 一键启动应用服务

完成基础设施和端口转发后，可以一键启动 AI HTTP 服务、AI Celery worker、Gateway 和 Flutter client：

```bash
cd /Users/zhushuangquan/Downloads/MKC
./scripts/local-dev-up.sh
```

脚本默认配置：

| 服务 | 默认值 |
|---|---|
| AI Service | `http://localhost:5001` |
| AI Celery worker | `default,transcribe,parse_pdf,embed,rag` queues |
| Gateway | `http://localhost:8080` |
| Flutter device | `chrome` |
| Client API | `http://localhost:8080/api/v1` |
| Storage host | `localhost` |

停止脚本启动的应用进程：

```bash
./scripts/local-dev-down.sh
```

日志与 PID 文件保存在 `.mkc-dev/`，该目录不会提交到 Git。解析 MP3/PDF、进度更新和自动摘要都依赖 AI Celery worker；如果没有 worker，任务会停在“等待中 0%”。

如需覆盖默认值：

```bash
CLIENT_DEVICE=macos AI_PORT=5001 GATEWAY_PORT=8080 ./scripts/local-dev-up.sh
```

如需让聊天走本地 Ollama 的 `deepseek-r1:8b`，先确认 Ollama 已启动并拉取模型：

```bash
ollama pull deepseek-r1:8b

LLM_PROVIDER=ollama \
LLM_MODEL=deepseek-r1:8b \
LLM_BASE_URL=http://localhost:11434/v1 \
LLM_API_KEY=ollama \
./scripts/local-dev-up.sh
```

### 3. 手动启动 AI Service

```bash
cd /Users/zhushuangquan/Downloads/MKC/ai-service

python -m venv .venv
source .venv/bin/activate
make install

cp config/.env.example .env
```

修改 `ai-service/.env` 的本地开发配置：

```env
INTERNAL_API_KEY=dev-internal-key
REDIS_URL=redis://:dev-redis@localhost:6379/0
CELERY_BROKER_URL=redis://:dev-redis@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:dev-redis@localhost:6379/1
MINIO_ACCESS_KEY=mkc
MINIO_SECRET_KEY=dev-minio
MINIO_BUCKET=mkc-resources
MINIO_ENDPOINT=localhost:9000
PORT=5001

# Local development can use mock providers to avoid remote API calls.
EMBEDDING_PROVIDER=mock
LLM_PROVIDER=mock
```

如果要使用本地 Ollama 的 DeepSeek R1，把 LLM 配置改成：

```env
LLM_PROVIDER=ollama
LLM_MODEL=deepseek-r1:8b
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
```

启动 HTTP 服务。本地验证使用 `5001` 端口；如果当前 shell 里存在 `DEBUG=release` 等非布尔值环境变量，需要显式覆盖为 `DEBUG=false`。推荐用 `python -m flask`，避免虚拟环境中 `flask` 命令入口指向旧 Python 解释器：

```bash
cd /Users/zhushuangquan/Downloads/MKC/ai-service
source .venv/bin/activate

set -a
source .env
DEBUG=false
PORT=5001
set +a

python -m flask --app app.main:create_app run \
  --host=0.0.0.0 \
  --port=5001 \
  --no-debugger \
  --no-reload
```

验证：

```bash
curl http://localhost:5001/api/v1/health
```

解析 MP3/PDF、进度更新和自动摘要都依赖 Celery worker。另开终端启动 worker，并保持运行：

```bash
cd /Users/zhushuangquan/Downloads/MKC/ai-service
source .venv/bin/activate
set -a
source .env
set +a
make worker
```

`make worker` 会显式使用 `DEBUG=false` 和 `celery_workers.celery_app`，避免当前 shell 中 `DEBUG=release` 等非布尔值导致 Celery 无法加载。可用下面命令确认 worker 在线且任务注册完整：

```bash
DEBUG=false celery -A celery_workers.celery_app inspect registered
```

### 4. 手动启动 Gateway

```bash
cd /Users/zhushuangquan/Downloads/MKC/gateway
cp config/config.example.yaml config/config.yaml
```

`gateway/config/config.yaml` 中已默认使用本机依赖地址，但密钥和密码建议通过环境变量注入，不写入配置文件。确认 `ai_service.base_url` 使用 `5001`：

```yaml
ai_service:
  base_url: http://localhost:5001
```

启动 Gateway：

```bash
cd /Users/zhushuangquan/Downloads/MKC/gateway

APP_MYSQL_PASSWORD=dev-mkc \
APP_REDIS_PASSWORD=dev-redis \
APP_JWT_SECRET=dev-jwt-secret \
APP_AI_SERVICE_BASE_URL=http://localhost:5001 \
APP_AI_SERVICE_INTERNAL_KEY=dev-internal-key \
APP_MINIO_ACCESS_KEY=mkc \
APP_MINIO_SECRET_KEY=dev-minio \
go run ./cmd/server
```

验证：

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/health
```

### 5. 手动启动 Flutter Client

```bash
cd /Users/zhushuangquan/Downloads/MKC/client

flutter pub get
flutter run \
  --dart-define=BASE_URL=http://localhost:8080/api/v1 \
  --dart-define=STORAGE_HOST=localhost
```

如果运行 Web：

```bash
flutter run -d chrome \
  --dart-define=BASE_URL=http://localhost:8080/api/v1 \
  --dart-define=STORAGE_HOST=localhost
```

### 推荐启动顺序

```text
1. ./infra/scripts/local-up.sh
2. ./infra/scripts/port-forward.sh
3. ai-service HTTP: python -m flask --app app.main:create_app run --host=0.0.0.0 --port=5001 --no-debugger --no-reload
4. ai-service Celery worker: make worker
5. gateway: go run ./cmd/server
6. client: flutter run --dart-define=BASE_URL=http://localhost:8080/api/v1 --dart-define=STORAGE_HOST=localhost
```

更多说明见 [docs/](./docs/) 目录。

## 目录结构

见 [技术文档 TECH_S0-1](./docs/tech/TECH_S0-1_github_repo_init.md)。

## API 文档

API 接口契约位于 [docs/api/openapi.yaml](docs/api/openapi.yaml)，设计说明见 [docs/api/api-design.md](docs/api/api-design.md)。

Gateway 启动后，可通过 Swagger UI 在线查看文档：

```text
http://mkc.local/swagger/index.html
```

本地开发环境请替换 `mkc.local` 为实际服务地址。

## License

MIT
