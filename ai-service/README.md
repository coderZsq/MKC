# MKC AI Service

Python AI 服务骨架，基于 Flask + Celery + Redis，为多媒体知识助手提供 ASR、PDF 解析、Embedding、RAG 等 AI 能力入口。

## 目录结构

```
ai-service/
├── app/                    # Flask 应用
│   ├── api/                # API 路由（health、internal）
│   ├── core/               # 配置、响应信封、异常、日志
│   ├── middleware/         # 请求 ID、请求日志、内部认证
│   ├── models/             # 数据模型（后续扩展）
│   ├── services/           # 业务服务层（后续扩展）
│   ├── tasks/              # Celery 任务
│   ├── extensions.py       # Redis 客户端
│   └── main.py             # 应用工厂
├── celery_workers/         # Celery Worker 入口与示例任务
├── config/                 # 配置文件与 .env 示例
├── models/                 # 模型权重（gitignored）
├── tests/                  # 单元测试
├── Dockerfile
├── Makefile
└── README.md
```

## 环境要求

- Python 3.11+
- Redis 6+（可选，缺失时服务可降级启动）

## 快速启动

```bash
cd ai-service
python -m venv .venv
source .venv/bin/activate
make install
cp config/.env.example .env
# 修改 .env 中的 INTERNAL_API_KEY
make run
```

服务默认监听 `5000`，访问：

```bash
curl http://localhost:5000/api/v1/health
```

## 环境变量

| 变量 | 说明 | 示例 |
|---|---|---|
| `INTERNAL_API_KEY` / `GATEWAY_INTERNAL_KEY` | 内部调用密钥（必填） | `dev-internal-key` |
| `REDIS_URL` | Redis 连接地址 | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Celery broker | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery 结果后端 | `redis://redis:6379/1` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `PORT` | 服务端口 | `5000` |
| `EMBEDDING_PROVIDER` | Embedding 提供方（ollama/zhipuai/openai/opensource/mock） | `ollama` |
| `EMBEDDING_MODEL` | Embedding 模型 | `bge-m3` |
| `EMBEDDING_BASE_URL` | Embedding 服务地址（ollama/openai 兼容端点） | `http://localhost:11434/v1` |
| `EMBEDDING_DIMENSIONS` | Embedding 向量维度 | `1024` |
| `VECTOR_STORE_DIMENSIONS` | 向量库集合维度（**必须与 `EMBEDDING_DIMENSIONS` 一致**） | `1024` |
| `LLM_PROVIDER` | LLM 提供方（ollama/zhipuai/openai/mock） | `ollama` |
| `ZHIPU_API_KEY` | ZhipuAI 密钥（`zhipuai` 时必填） | `change-me` |

> 切换 embedding 模型或维度后，`VECTOR_STORE_DIMENSIONS` 必须同步修改，并删除本地 `ai-service/milvus.db`（或 drop 向量集合）后重建，否则向量写入会因维度不匹配失败。

## 常用命令

```bash
# 运行测试
make test

# 代码检查
make lint

# 格式化
make format

# 启动 Celery worker
make worker

# 启动 Flower 监控
make flower

# 构建 Docker 镜像
make build
```

MP3 转写、PDF 解析、进度回调和自动摘要都由 Celery worker 异步执行。只启动 Flask HTTP 服务只能接收任务，不能消费队列；任务会一直停在 `pending / 0%`。

本地启动 worker 时建议先加载 `.env`：

```bash
source .venv/bin/activate
set -a
source .env
set +a
make worker
```

`make worker` 会显式设置 `DEBUG=false` 并使用 `celery_workers.celery_app`。如果当前 shell 中存在 `DEBUG=release` 等非布尔值，直接运行 `celery ...` 会导致配置解析失败；请通过 `make worker` 启动。

确认 worker 在线和任务注册：

```bash
DEBUG=false celery -A celery_workers.celery_app inspect registered
```

## 健康检查

`GET /api/v1/health` 返回统一响应信封：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "ai-service",
    "dependencies": {
      "redis": "down",
      "celery_broker": "down"
    }
  },
  "error": null,
  "meta": {
    "timestamp": "2026-07-07T00:00:00+00:00"
  }
}
```

当 Redis 或 Celery broker 不可用时，`dependencies` 对应项为 `down`，服务仍可响应。

## 内部认证

AI Service 不直接暴露公网，仅接受 Gateway 内部调用。内部接口（如 `/api/v1/internal/*`）需要请求头：

```bash
curl -H "X-Internal-Key: $INTERNAL_API_KEY" http://localhost:5000/api/v1/internal/health
```

## Docker

```bash
make build
docker run -e INTERNAL_API_KEY=dev-internal-key -p 5000:5000 mkc-ai-service:latest
```

镜像使用多阶段构建，运行时以非 root 用户运行。

## Kubernetes

`k8s/` 目录提供最小可运行的部署草稿，需根据实际环境补充镜像仓库、Secret 等：

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

> 当前 Sprint 0 仅包含基础骨架、`/api/v1/health` 与内部认证，业务 API 将在后续 Sprint 补充。
