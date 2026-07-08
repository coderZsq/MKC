# S0-8 测试用例：Python AI Service 骨架

## 1. 范围与目标

验证 `ai-service/` 目录下 Python 服务已按 Flask application factory 初始化，包含 Celery 任务队列、Redis broker/backend、pydantic-settings 配置、gunicorn+gevent 部署入口、pytest 测试、代码格式化与类型检查，并支持与 Gateway 的内部认证。

## 2. 测试环境

- Python 3.11 已安装
- 本地 Redis 容器或 K8s Redis 可选
- 已创建虚拟环境并安装依赖：`pip install -r requirements.txt -r requirements-dev.txt`

## 3. 测试用例

### 3.1 目录结构与文件存在性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-001 | Functional | Static | P0 | `ai-service/` 目录存在 | 仓库已克隆 | `ls ai-service/` | 目录存在 | PRD AC-1 |
| MKC-TC-S0-8-002 | Functional | Static | P0 | `ai-service/app/__init__.py` 应用工厂存在 | 仓库已克隆 | `ls ai-service/app/__init__.py` | 文件存在 | PRD AC-2 |
| MKC-TC-S0-8-003 | Functional | Static | P0 | `ai-service/app/api/`、`app/services/`、`app/tasks/` 分层存在 | 仓库已克隆 | `ls -d ai-service/app/api ai-service/app/services ai-service/app/tasks ai-service/app/core ai-service/app/models 2>/dev/null` | 关键分层目录均存在 | PRD AC-2 |
| MKC-TC-S0-8-004 | Functional | Static | P1 | `ai-service/app/core/` 包含配置与日志 | 仓库已克隆 | `ls ai-service/app/core/` | 存在 config.py / logger.py | PRD 推荐目录结构 |
| MKC-TC-S0-8-005 | Functional | Static | P1 | `ai-service/tests/` 目录存在 | 仓库已克隆 | `ls ai-service/tests/` | 目录存在且至少有一个测试文件 | PRD AC-8 |
| MKC-TC-S0-8-006 | Functional | Static | P1 | 依赖文件 `requirements.txt` 与 `requirements-dev.txt` 存在 | 仓库已克隆 | `ls ai-service/requirements*.txt` | 两个文件均存在 | PRD AC-1 |
| MKC-TC-S0-8-007 | Functional | Static | P1 | `ai-service/Dockerfile` 存在 | 仓库已克隆 | `ls ai-service/Dockerfile` | 文件存在 | PRD AC-7 |
| MKC-TC-S0-8-008 | Functional | Static | P1 | `ai-service/Makefile` 存在 | 仓库已克隆 | `ls ai-service/Makefile` | 文件存在 | PRD AC-9 |
| MKC-TC-S0-8-009 | Boundary | Static | P2 | 单文件行数符合小文件原则 | 仓库已克隆 | `find ai-service/app -name "*.py" -exec wc -l {} + | sort -n | tail -10` | 单文件不超过 800 行 | 代码规范 |

### 3.2 依赖声明

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-010 | Functional | Static | P0 | `requirements.txt` 声明 Flask | 文件存在 | `grep -i "^Flask" ai-service/requirements.txt` | 版本形如 `3.0.x` | PRD 核心依赖 |
| MKC-TC-S0-8-011 | Functional | Static | P0 | `requirements.txt` 声明 Celery | 文件存在 | `grep -i "^celery" ai-service/requirements.txt` | 版本形如 `5.4.x` | PRD 核心依赖 |
| MKC-TC-S0-8-012 | Functional | Static | P0 | `requirements.txt` 声明 Redis 客户端 | 文件存在 | `grep -i "^redis" ai-service/requirements.txt` | 存在 | PRD 核心依赖 |
| MKC-TC-S0-8-013 | Functional | Static | P1 | `requirements.txt` 声明 `pydantic-settings` | 文件存在 | `grep -i "pydantic-settings" ai-service/requirements.txt` | 存在 | PRD 核心依赖 |
| MKC-TC-S0-8-014 | Functional | Static | P1 | `requirements.txt` 声明 `gunicorn` 与 `gevent` | 文件存在 | `grep -i "^gunicorn\|^gevent" ai-service/requirements.txt` | 均存在 | PRD 部署方式 |
| MKC-TC-S0-8-015 | Functional | Static | P1 | `requirements-dev.txt` 声明 `pytest`、`black`、`ruff`、`mypy` | 文件存在 | `grep -iE "^pytest|^black|^ruff|^mypy" ai-service/requirements-dev.txt` | 均存在 | PRD AC-6 |
| MKC-TC-S0-8-016 | Functional | Static | P1 | 依赖已锁定或指定最小版本 | 文件存在 | 检查 requirements 文件 | 所有包都有版本约束 | 工程最佳实践 |

### 3.3 依赖安装与基础运行

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-017 | Functional | Integration | P0 | `pip install` 成功 | 虚拟环境已创建 | `pip install -r requirements.txt -r requirements-dev.txt` | 无依赖冲突或 fatal error | PRD AC-1 |
| MKC-TC-S0-8-018 | Functional | Integration | P0 | Flask 应用工厂可被导入 | 依赖已安装 | `python -c "from app import create_app; app = create_app()"` | 无异常 | PRD AC-2 |
| MKC-TC-S0-8-019 | Functional | Integration | P0 | Flask 开发服务器可启动 | 依赖已安装 | `FLASK_APP=app FLASK_ENV=development flask run` | 监听 5000 端口，无启动异常 | PRD AC-3 |
| MKC-TC-S0-8-020 | Functional | Integration | P1 | gunicorn + gevent 可启动 | 依赖已安装 | `gunicorn -k gevent -w 1 -b 0.0.0.0:5000 "app:create_app()"` | 启动成功，可响应请求 | PRD 部署方式 |
| MKC-TC-S0-8-021 | Functional | Integration | P1 | Celery worker 可启动 | 依赖已安装，Redis 可达 | `celery -A app.tasks worker --loglevel=info` | worker 启动成功，等待任务 | PRD AC-4 |
| MKC-TC-S0-8-022 | Functional | Integration | P1 | Celery beat 可启动（如有时） | 依赖已安装 | `celery -A app.tasks beat --loglevel=info` | beat 启动成功 | PRD 可选 |

### 3.4 配置管理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-023 | Functional | Static | P0 | `app/core/config.py` 使用 pydantic-settings | 文件存在 | 阅读 `app/core/config.py` | 继承 `BaseSettings`，从环境变量读取配置 | PRD 核心依赖 |
| MKC-TC-S0-8-024 | Functional | Unit | P1 | 环境变量正确映射到配置对象 | 代码存在 | 运行 config 测试 | 设置 `REDIS_URL`、`INTERNAL_API_KEY` 后可读取 | PRD 技术要点 |
| MKC-TC-S0-8-025 | Negative | Unit | P1 | 缺少必填配置时启动失败并提示 | 代码存在 | 取消设置 `INTERNAL_API_KEY` 后测试 | 抛出 `ValidationError` 或明确提示 | PRD 技术要点 |
| MKC-TC-S0-8-026 | Functional | Unit | P1 | `.env` 文件可被加载 | 代码存在 | 创建 `.env` 并测试 | pydantic-settings 读取 `.env` 配置 | PRD 技术要点 |
| MKC-TC-S0-8-027 | Security | Static | P0 | 配置文件/示例不包含真实密钥 | 文件存在 | `cat ai-service/.env.example` | 密码字段为占位符 | 安全基线 |

### 3.5 内部认证

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-028 | Security | Static | P0 | 内部接口校验 `X-Internal-Key` | 文件存在 | 阅读 `app/api/dependencies.py` 或 middleware | 存在 `X-Internal-Key` 校验逻辑 | PRD AC-5 |
| MKC-TC-S0-8-029 | Security | Integration | P0 | 缺少 `X-Internal-Key` 返回 401 | 服务运行 | `curl http://localhost:5000/api/v1/internal/health` | 返回 401 / 403 | PRD AC-5 |
| MKC-TC-S0-8-030 | Security | Integration | P0 | 错误的 `X-Internal-Key` 返回 401 | 服务运行 | `curl -H "X-Internal-Key: wrong" ...` | 返回 401 / 403 | PRD AC-5 |
| MKC-TC-S0-8-031 | Security | Integration | P1 | 正确的 `X-Internal-Key` 可访问内部接口 | 服务运行 | `curl -H "X-Internal-Key: $INTERNAL_API_KEY" ...` | 返回 200 | PRD AC-5 |
| MKC-TC-S0-8-032 | Security | Static | P1 | `INTERNAL_API_KEY` 从环境变量读取 | 代码存在 | 搜索硬编码 key | 无硬编码 | 安全基线 |

### 3.6 API 路由与健康检查

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-033 | Functional | Integration | P0 | `/api/v1/health` 返回服务健康状态 | 服务运行 | `curl http://localhost:5000/api/v1/health` | 返回 JSON，status 为 ok | PRD AC-5 |
| MKC-TC-S0-8-034 | Functional | Unit | P1 | 健康检查 handler 返回统一响应信封 | 代码存在 | 运行 health 测试 | 返回 `{success, data, error, meta}` | PRD API 设计 |
| MKC-TC-S0-8-035 | Functional | Static | P1 | 蓝图按功能模块拆分 | 文件存在 | `ls ai-service/app/api/routes/` | 存在 `health.py`、`*_tasks.py` 等 | PRD AC-2 |
| MKC-TC-S0-8-036 | Functional | Unit | P2 | 未匹配路由返回统一 404 信封 | 代码存在 | 测试 `/not-exist` | 返回 404 + `{success:false, error:{code,message}}` | PRD API 设计 |

### 3.7 Celery 任务

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-037 | Functional | Integration | P0 | 示例 Celery 任务可被调用 | worker 运行 | `celery -A app.tasks call app.tasks.sample.hello --args='["world"]'` | 任务执行成功，结果写入 Redis backend | PRD AC-4 |
| MKC-TC-S0-8-038 | Functional | Integration | P1 | 任务失败时记录异常不崩溃 worker | worker 运行 | 调用会抛出异常的测试任务 | worker 捕获异常，任务状态为 FAILURE | PRD 错误处理 |
| MKC-TC-S0-8-039 | Functional | Unit | P1 | 任务函数单元测试存在 | 代码存在 | `find ai-service/tests -name "*test*.py"` | 至少存在一个测试文件 | PRD AC-8 |
| MKC-TC-S0-8-040 | Functional | Integration | P2 | 任务重试策略配置正确 | 任务存在 | 查看任务装饰器 | `autoretry_for`、`retry_backoff` 等参数配置合理 | PRD 技术要点 |

### 3.8 代码质量与测试

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-041 | Functional | Integration | P0 | `pytest` 通过 | 依赖已安装 | `cd ai-service && pytest` | 至少基础测试通过 | PRD AC-8 |
| MKC-TC-S0-8-042 | Functional | Integration | P1 | `ruff check .` 通过 | 依赖已安装 | `cd ai-service && ruff check .` | 无 error | PRD AC-6 |
| MKC-TC-S0-8-043 | Functional | Integration | P1 | `black --check .` 通过 | 依赖已安装 | `cd ai-service && black --check .` | 无格式错误 | PRD AC-6 |
| MKC-TC-S0-8-044 | Functional | Integration | P2 | `mypy app` 通过 | 依赖已安装 | `cd ai-service && mypy app` | 无 type error | PRD AC-6 |
| MKC-TC-S0-8-045 | Functional | Integration | P1 | 测试覆盖率报告生成 | 测试存在 | `pytest --cov=app --cov-report=term-missing` | 输出覆盖率，后续可配置 80% 阈值 | PRD 测试策略 |
| MKC-TC-S0-8-046 | Idempotency | Integration | P2 | 重复 `pytest` 结果一致 | 测试已通过 | 连续运行 3 次 | 结果一致 | 工程最佳实践 |

### 3.9 Docker 与部署

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-047 | Functional | Static | P1 | Dockerfile 使用 Python 3.11 slim | 文件存在 | `head -n 5 ai-service/Dockerfile` | 基础镜像为 `python:3.11-slim` 或等效 | PRD AC-7 |
| MKC-TC-S0-8-048 | Functional | Integration | P1 | Docker 镜像构建成功 | Docker 可用 | `docker build -t mkc-ai-service:latest ai-service/` | 构建成功 | PRD AC-7 |
| MKC-TC-S0-8-049 | Functional | Integration | P2 | 容器启动后健康检查通过 | 镜像已构建 | `docker run -e INTERNAL_API_KEY=xxx -p 5000:5000 mkc-ai-service:latest` | `/api/v1/health` 返回 200 | PRD AC-7 |
| MKC-TC-S0-8-050 | Security | Static | P2 | Dockerfile 使用非 root 用户 | 文件存在 | `grep -E "USER|RUN adduser" ai-service/Dockerfile` | 使用非 root 运行 | 安全基线 |

### 3.10 Makefile 与脚本

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-051 | Functional | Static | P1 | Makefile 包含 install/test/lint/format/run 目标 | 文件存在 | `cat ai-service/Makefile` | 包含 `install`、`test`、`lint`、`format`、`run` | PRD AC-9 |
| MKC-TC-S0-8-052 | Functional | Integration | P1 | `make test` 成功 | 依赖已安装 | `cd ai-service && make test` | 运行 pytest 并通过 | PRD AC-9 |
| MKC-TC-S0-8-053 | Functional | Integration | P1 | `make lint` 成功 | 依赖已安装 | `cd ai-service && make lint` | 运行 ruff/black/mypy 无错误 | PRD AC-9 |
| MKC-TC-S0-8-054 | Functional | Integration | P2 | `make run` 启动开发服务器 | 依赖已安装 | `cd ai-service && make run` | Flask 开发服务器启动 | PRD AC-9 |

### 3.11 日志、错误处理与边界

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-8-055 | Functional | Static | P1 | 统一响应信封函数存在 | 文件存在 | `ls ai-service/app/core/response.py` 或等效 | 存在 response.py | PRD API 设计 |
| MKC-TC-S0-8-056 | Functional | Unit | P1 | 统一响应函数返回正确结构 | 代码存在 | 运行 response 测试 | success/error 格式与 API 规范一致 | PRD API 设计 |
| MKC-TC-S0-8-057 | Functional | Integration | P1 | 日志输出为 JSON 或结构化文本 | 服务运行 | 发起请求并查看日志 | 包含时间、level、request_id 等 | PRD 可观测性 |
| MKC-TC-S0-8-058 | Exception | Integration | P1 | Redis 不可用时 Celery worker 给出明确错误 | Redis 未启动 | 启动 worker | 日志提示无法连接 broker 并退出 | PRD 错误处理 |
| MKC-TC-S0-8-059 | Boundary | Integration | P2 | 大请求体不导致 worker 阻塞 | 代码存在 | 压力测试上传接口 | gunicorn gevent worker 可并发处理 | PRD 部署方式 |
| MKC-TC-S0-8-060 | Concurrency | Integration | P2 | 多 worker 同时消费任务不丢失 | worker 运行 | 同时发起多个任务 | 每个任务执行一次，结果一致 | PRD 可扩展性 |

## 4. 测试执行清单

- [ ] `ai-service/app/__init__.py` 应用工厂可被导入
- [ ] `requirements.txt` / `requirements-dev.txt` 包含 PRD 核心依赖
- [ ] `pip install` 成功且无冲突
- [ ] `pytest` 通过
- [ ] `ruff check .` / `black --check .` / `mypy app` 通过
- [ ] `/api/v1/health` 返回统一响应
- [ ] 内部接口 `X-Internal-Key` 认证生效
- [ ] Celery worker 可启动并执行任务
- [ ] Dockerfile 构建成功
- [ ] Makefile 常用目标可用
- [ ] 无硬编码密钥/密码

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
