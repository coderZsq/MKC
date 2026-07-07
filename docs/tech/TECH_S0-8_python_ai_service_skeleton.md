# 技术文档：[S0-8] Python AI Service 项目骨架与架构设计

> 版本：v1.0  
> 日期：2026-07-06  > 作者：朱双泉  > 级别：架构师/AI 服务负责人  > 关联 PRD：[PRD_S0-8_python_ai_service_skeleton.md](../prd/PRD_S0-8_python_ai_service_skeleton.md)

---

## 1. 文档目标

本文档定义 MKC 项目 Python AI Service 的架构设计、目录结构、Flask 应用工厂、Celery 异步任务队列、配置管理、依赖注入、统一响应、错误处理、健康检查、Dockerfile、K8s 部署以及后续 AI 模块扩展预留。

---

## 2. 技术栈

| 依赖 | 版本 | 用途 |
|---|---|---|
| Flask | 3.0.x | Web 框架 |
| Celery | 5.4+ | 异步任务队列 |
| Redis | 5.x | Broker + Backend |
| pydantic-settings | 2.x | 配置管理 |
| gunicorn | 22.x | 生产 WSGI 服务器 |
| pytest | 8.x | 测试 |
| black / ruff / mypy | 24.x / 0.5+ / 1.10+ | 代码质量 |
| open-telemetry | 1.25+ | 可观测性 |

后续 Sprint 补充：
- faster-whisper, torch
- pymupdf, pdfplumber
- langgraph, langchain, llama-index
- sentence-transformers, BGE-M3

---

## 3. 项目分层

```
ai-service/
├── app/                        # Flask 应用
│   ├── __init__.py
│   ├── main.py                 # 应用工厂
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── tasks.py            # 任务触发接口（可选）
│   ├── core/                   # 核心模块
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── response.py
│   ├── services/               # 业务服务层（后续扩展）
│   │   ├── __init__.py
│   │   ├── asr_service.py
│   │   ├── pdf_service.py
│   │   ├── embedding_service.py
│   │   └── rag_service.py
│   └── extensions.py           # 扩展初始化
├── celery_workers/             # Celery Worker
│   ├── __init__.py
│   ├── celery_app.py           # Celery 实例
│   └── tasks/
│       ├── __init__.py
│       ├── example_task.py
│       ├── transcribe_task.py  # 后续
│       └── parse_pdf_task.py   # 后续
├── config/
│   ├── .env.example
│   └── settings.yaml
├── models/                     # 模型权重（gitignore）
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_health.py
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── celeryconfig.py
├── Makefile
└── README.md
```

---

## 4. 配置管理

### 4.1 pydantic-settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "mkc-ai-service"
    debug: bool = True
    env: str = "dev"
    port: int = 5000

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/1"

    gateway_internal_key: str = "change-me"
    log_level: str = "INFO"

settings = Settings()
```

### 4.2 环境变量示例

```bash
APP_NAME=mkc-ai-service
DEBUG=True
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1
GATEWAY_INTERNAL_KEY=dev-internal-key
```

---

## 5. Flask 应用工厂

```python
from flask import Flask
from app.core.config import settings
from app.extensions import celery, redis_client
from app.api import health_bp, tasks_bp
from app.core.response import make_response
from app.core.exceptions import APIException

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(settings)

    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)

    return app

def register_extensions(app: Flask) -> None:
    celery.conf.update(app.config)
    redis_client.from_url(settings.redis_url)

def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp, url_prefix="/health")
    app.register_blueprint(tasks_bp, url_prefix="/api/v1/tasks")

def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(APIException)
    def handle_api_exception(error: APIException):
        return make_response(
            success=False,
            error={"code": error.code, "message": error.message},
            status=error.status_code,
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception):
        return make_response(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
            status=500,
        )
```

---

## 6. Celery 配置

### 6.1 celery_app.py

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "ai-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["celery_workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    task_routes={
        "celery_workers.tasks.transcribe.*": {"queue": "transcribe"},
        "celery_workers.tasks.parse_pdf.*": {"queue": "parse_pdf"},
        "celery_workers.tasks.embed.*": {"queue": "embed"},
        "celery_workers.tasks.rag.*": {"queue": "rag"},
    },
)
```

### 6.2 示例任务

```python
from celery_workers.celery_app import celery_app
import time

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def example_task(self, name: str) -> str:
    try:
        for i in range(5):
            self.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": 5},
            )
            time.sleep(1)
        return f"Hello, {name}!"
    except Exception as exc:
        raise self.retry(exc=exc)
```

### 6.3 任务状态广播

任务进度通过 Celery `update_state` 写入 Redis backend，Gateway 通过 `task_id` 轮询或 SSE 推送。

---

## 7. 统一响应与错误处理

### 7.1 response.py

```python
from flask import jsonify
from datetime import datetime, timezone
from typing import Any, Optional

def make_response(
    data: Any = None,
    success: bool = True,
    error: Optional[dict] = None,
    meta: Optional[dict] = None,
    status: int = 200,
):
    payload = {
        "success": success,
        "data": data,
        "error": error,
        "meta": meta or {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    return jsonify(payload), status
```

### 7.2 exceptions.py

```python
class APIException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ValidationException(APIException):
    def __init__(self, message: str = "参数校验失败"):
        super().__init__("VALIDATION_ERROR", message, 400)
```

---

## 8. 健康检查

```python
from flask import Blueprint
from app.core.response import make_response
from app.extensions import redis_client
from celery_workers.celery_app import celery_app

health_bp = Blueprint("health", __name__)

@health_bp.get("/")
def health():
    redis_ok = redis_client.ping()
    broker_ok = celery_app.control.ping(timeout=1.0) is not None

    data = {
        "status": "ok" if redis_ok and broker_ok else "degraded",
        "service": "ai-service",
        "dependencies": {
            "redis": "ok" if redis_ok else "down",
            "celery_broker": "ok" if broker_ok else "down",
        },
    }

    status = 200 if data["status"] == "ok" else 503
    return make_response(data=data, status=status)
```

---

## 9. 内部认证

AI Service 不直接暴露公网，仅接受 Gateway 内部调用。通过 `X-Internal-Key` 头部验证：

```python
from functools import wraps
from flask import request
from app.core.config import settings
from app.core.exceptions import APIException

def require_internal_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-Internal-Key")
        if key != settings.gateway_internal_key:
            raise APIException("UNAUTHORIZED", "非法内部调用", 401)
        return f(*args, **kwargs)
    return decorated
```

---

## 10. Dockerfile

```dockerfile
# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY requirements.txt requirements-dev.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-k", "gevent", "-b", "0.0.0.0:5000", "app.main:create_app()"]
```

**说明**：
- 多阶段构建减少镜像体积
- 安装 ffmpeg 为后续 faster-whisper 做准备
- 生产使用 gevent worker 处理 SSE 长连接

---

## 11. K8s 部署初稿

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-service
  namespace: mkc-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-service
  template:
    metadata:
      labels:
        app: ai-service
    spec:
      containers:
        - name: ai-service
          image: mkc-ai-service:latest
          ports:
            - containerPort: 5000
          envFrom:
            - secretRef:
                name: ai-service-secret
          resources:
            requests:
              memory: "512Mi"
              cpu: "200m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: ai-service
  namespace: mkc-dev
spec:
  selector:
    app: ai-service
  ports:
    - port: 5000
      targetPort: 5000
```

---

## 12. Makefile

```makefile
.PHONY: install format lint test worker flower run build

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

format:
	black app celery_workers tests
	ruff check --fix app celery_workers tests

lint:
	ruff check app celery_workers tests
	mypy app

test:
	pytest --cov=app --cov-report=term-missing

worker:
	celery -A celery_workers.celery_app worker -l info -Q default,transcribe,parse_pdf,embed,rag

flower:
	celery -A celery_workers.celery_app flower --port=5555

run:
	flask --app app.main:create_app run --host=0.0.0.0 --port=5000 --debug

build:
	docker build -t mkc-ai-service:latest .
```

---

## 13. 后续 AI 模块扩展预留

| 模块 | 入口文件 | 说明 |
|---|---|---|
| ASR | `services/asr_service.py` | faster-whisper 封装 |
| PDF 解析 | `services/pdf_service.py` | pymupdf / pdfplumber |
| Embedding | `services/embedding_service.py` | BGE-M3 / text-embedding-v3 |
| 向量存储 | `services/vector_store.py` | Milvus 客户端 |
| RAG | `services/rag_service.py` | LangGraph + LlamaIndex |
| LLM | `services/llm_service.py` | OpenAI / 智谱 / Ollama |

---

## 14. 检查清单

- [ ] Python 虚拟环境创建
- [ ] Flask 应用工厂跑通
- [ ] Celery Worker 启动成功
- [ ] Redis broker 连通性验证
- [ ] 健康检查接口可访问
- [ ] 统一响应和错误处理实现
- [ ] 内部认证中间件实现
- [ ] pytest 通过 health 接口测试
- [ ] Dockerfile 构建成功
- [ ] K8s deployment manifest 编写完成
- [ ] README 说明启动和目录结构
