# PRD：[S0-8] 搭建 Python AI Service 项目骨架

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](./AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-8 |
| **任务名称** | 搭建 Python AI Service 项目骨架 |
| **所属史诗** | E0 基础设施 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S0-1 仓库初始化 |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要在 `ai-service/` 目录下搭建一个基于 Flask 的 Python AI 服务项目骨架，集成 Celery 异步任务队列、配置管理、健康检查接口和统一的 API 响应格式。该服务将作为 faster-whisper ASR、PDF 解析、Embedding、RAG 问答和 LangGraph Agent 的承载体。

---

## 验收标准（AC）

- [ ] 使用 `python -m venv .venv` 初始化虚拟环境，并创建 `requirements.txt`
- [ ] 项目目录按 `app/`、`celery_workers/`、`config/`、`models/`、`tests/` 分层
- [ ] 集成 Flask Web 框架
- [ ] 集成 Celery + Redis 作为 broker
- [ ] 实现配置管理（pydantic-settings），支持 dev/prod 环境
- [ ] 实现 `/health` 健康检查接口，返回服务状态和依赖状态
- [ ] 实现统一的 API 响应封装和错误处理
- [ ] 实现一个示例 Celery Task，可通过 worker 执行
- [ ] `pytest` 通过（至少包含 health 接口测试）
- [ ] 编写 Dockerfile 和 K8s deployment 初稿
- [ ] README 说明启动命令、环境变量和目录结构

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py                   # Flask 应用工厂
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py             # 健康检查路由
│   ├── core/
│   │   ├── config.py             # 配置
│   │   ├── exceptions.py         # 自定义异常
│   │   └── response.py           # 统一响应
│   └── extensions.py             # Celery、Redis 等扩展初始化
├── celery_workers/
│   ├── __init__.py
│   ├── celery_app.py             # Celery 应用实例
│   └── tasks/
│       ├── __init__.py
│       └── example_task.py       # 示例任务
├── config/
│   ├── .env.example
│   └── settings.yaml             # 可选配置文件
├── models/                       # 模型文件/权重目录（gitignore）
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── celeryconfig.py
├── Makefile
└── README.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Flask | 3.0.x | Web 框架 |
| celery | 5.4+ | 异步任务队列 |
| redis | 5.x | Redis 客户端（Celery broker + backend） |
| pydantic-settings | 2.x | 配置管理 |
| python-dotenv | 1.x | 环境变量加载 |
| gunicorn | 22.x | 生产 WSGI 服务器 |
| pytest | 8.x | 单元测试 |
| pytest-cov | 5.x | 覆盖率 |
| black | 24.x | 代码格式化 |
| ruff | 0.5+ | 代码 lint |

后续 Sprint 会补充：
- faster-whisper, torch, ffmpeg-python
- pymupdf, pdfplumber
- langgraph, langchain, llama-index
- openai / zhipuai SDK

---

## 技术要点

### 配置管理

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "mkc-ai-service"
    debug: bool = True
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/1"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Flask 应用工厂

```python
def create_app():
    app = Flask(__name__)
    app.config.from_object(settings)
    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    return app
```

### 统一响应封装

```python
def success(data=None, meta=None):
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "meta": meta
    })

def fail(code, err_code, message, status=400):
    return jsonify({
        "success": False,
        "data": None,
        "error": {"code": err_code, "message": message},
        "meta": None
    }), status
```

### Celery 配置

```python
celery_app = Celery(
    "ai-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["celery_workers.tasks"]
)
```

### SSE 生产环境说明

后续 Sprint 实现 SSE 流式问答时，使用：
- `flask.stream_with_context`
- `Response(mimetype='text/event-stream')`
- 生产环境配合 Gunicorn + gevent/eventlet worker 处理长连接

---

## 文件位置

```
ai-service/
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   └── extensions.py
├── celery_workers/
│   ├── celery_app.py
│   └── tasks/
├── config/
├── tests/
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── Makefile
└── README.md
```

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 依赖包体积大（如 torch） | 镜像构建慢/本地安装慢 | Sprint 0 不安装 AI 依赖，仅搭骨架 |
| Celery 本地调试复杂 | 开发效率低 | 提供 Makefile 命令 `make worker` 和 `make flower` |
| Flask 与 Gunicorn 配置不熟悉 | SSE 生产不稳定 | 参考官方文档，开发阶段先用 Flask dev server |

---

## 备注

- 本任务只搭建骨架，不集成 AI 模型
- 示例 Celery Task 用于验证 worker 与 broker 连通性
- Dockerfile 采用多阶段构建，避免把 dev 依赖打进镜像
- 后续 Sprint 将在此骨架上扩展 ASR、PDF 解析、Embedding、RAG 等模块
