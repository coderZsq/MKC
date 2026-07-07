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
