# ASR 上传与转写链路排错手册

> 适用范围：MKC 多媒体知识助手 ASR（自动语音识别）上传→转写→结果获取全链路。
> 目标：帮助后端、算法与测试同学在本地联调、集成测试或线上排查时，快速定位并修复常见问题。

---

## 1. 背景与目标

ASR 上传与转写流程涉及 **Gateway**（Go 服务）与 **AI Service**（Python Flask + Celery）两个主进程，外加 **MinIO** 对象存储和 **Redis**（Celery 消息队列）。

本手册覆盖：
- 端到端调用链路（从客户端上传文件到客户端获取转写结果）
- 每个步骤的入口文件、关键行号与请求/响应报文
- 已踩过的坑及修复/预防方法
- 常用验证命令
- 当前未提交改动清单
- 上线/合并前检查项

---

## 2. 链路总览

| 组件 | 类型 | 端口 / 文件 | 职责 | 代码入口 |
|------|------|------------|------|----------|
| Client | 外部调用方 | `POST /api/v1/files/upload`<br>`GET /api/v1/tasks/{task_id}/result` | 上传媒体文件并获取转写结果 | - |
| Gateway FileHandler | HTTP Handler | `gateway/internal/handler/file_handler.go` | 处理 multipart 上传 | [`file_handler.go`](../../gateway/internal/handler/file_handler.go#L25-L56) |
| Gateway FileService | Service | `gateway/internal/service/file_service.go` | 校验文件、存 MinIO、创建 Resource 和 Task | [`file_service.go`](../../gateway/internal/service/file_service.go#L93-L177) |
| Gateway HTTPTaskDispatcher | Service | `gateway/internal/service/task_dispatcher.go` | 将 `media_parse` 任务派发到 AI Service ASR | [`task_dispatcher.go`](../../gateway/internal/service/task_dispatcher.go#L56-L133) |
| Gateway Router | Router | `gateway/internal/router/router.go` | 注册公共路由和内部路由 | [`router.go`](../../gateway/internal/router/router.go#L50-L70) |
| Gateway InternalTaskHandler | HTTP Handler | `gateway/internal/handler/internal_task_handler.go` | 接收 Worker 进度 / 状态更新 | [`internal_task_handler.go`](../../gateway/internal/handler/internal_task_handler.go#L37-L77) |
| Gateway TaskService | Service | `gateway/internal/service/task_service.go` | 更新任务进度与状态，发布 SSE 事件 | [`task_service.go`](../../gateway/internal/service/task_service.go#L257-L330) |
| Gateway ResultHandler | HTTP Handler | `gateway/internal/handler/result_handler.go` | 处理结果获取接口 | [`result_handler.go`](../../gateway/internal/handler/result_handler.go#L23-L34) |
| Gateway ResultService | Service | `gateway/internal/service/result_service.go` | 生成转写结果的预签名 URL | [`result_service.go`](../../gateway/internal/service/result_service.go#L66-L144) |
| Task model | Model | `gateway/internal/model/task.go` | 定义任务状态与类型常量 | [`task.go`](../../gateway/internal/model/task.go#L30-L42) |
| AI Service ASR API | Flask Blueprint | `ai-service/app/main.py:40`<br>`ai-service/app/api/asr.py` | 接收内部请求，校验音频并入队 Celery | [`asr.py`](../../ai-service/app/api/asr.py#L39-L67) |
| Celery Worker `run_asr` | Celery Task | `ai-service/celery_workers/tasks/asr_task.py` | 执行 ASR 转写主任务 | [`asr_task.py`](../../ai-service/celery_workers/tasks/asr_task.py#L34-L62) |
| BaseAITask | Celery Base | `ai-service/celery_workers/tasks/base.py` | 提供重试、成功/失败/重试生命周期钩子 | [`base.py`](../../ai-service/celery_workers/tasks/base.py#L35-L69) |
| AsrService | Service | `ai-service/app/services/asr_service.py` | 下载、预处理、转写、上传结果 | [`asr_service.py`](../../ai-service/app/services/asr_service.py#L67-L139) |
| WhisperEngine | Engine | `ai-service/app/services/whisper_engine.py` | 封装 `faster-whisper` 推理 | [`whisper_engine.py`](../../ai-service/app/services/whisper_engine.py#L55-L82) |
| AudioProcessor | Processor | `ai-service/app/services/audio_processor.py` | 将音频转 16kHz mono WAV 并读取时长 | [`audio_processor.py`](../../ai-service/app/services/audio_processor.py#L17-L45) |
| GatewayProgressReporter | Client | `ai-service/app/services/gateway_reporter.py` | 向 Gateway 内部端点上报进度与状态 | [`gateway_reporter.py`](../../ai-service/app/services/gateway_reporter.py#L31-L54) |
| AI configuration | Config | `ai-service/config/ai.yaml` | 配置 ASR 模型、重试、进度间隔、MinIO、Gateway | [`ai.yaml`](../../ai-service/config/ai.yaml) |

### 关键外部依赖
- **MinIO**：`mkc-resources` 桶存储原始上传文件；`results` 桶存储 `transcript.json` 与字幕文件。
- **Celery**：`run_asr` 队列承载异步转写任务。
- **ffmpeg**：用于音频预处理。
- **faster-whisper**：本地 ASR 推理。

---

## 3. 详细调用链

### 1. 接收 multipart 上传
- **执行方**：Gateway FileHandler
- **文件**：[`gateway/internal/handler/file_handler.go`](../../gateway/internal/handler/file_handler.go#L25-L56)
- **说明**：客户端以 `multipart/form-data` 提交 `file` 字段；Handler 提取 `user_id/user_uuid`，校验 `Content-Length` 不超过 500MB，解析表单文件后调用 `FileService.Upload`。

### 2. 校验文件并创建 Resource + Task
- **执行方**：Gateway FileService
- **文件**：[`gateway/internal/service/file_service.go`](../../gateway/internal/service/file_service.go#L93-L177)
- **说明**：检查缺失头、大小限制、声明的 MIME 白名单、读取前 512 字节校验兼容性；上传 MinIO；创建 Resource（`status=1 uploading`）；创建 Task（`type=media_parse, status=pending`）；若为 `media_parse` 或 `pdf_parse` 则自动派发。返回 `UploadResult`。
- **响应示例**：
  ```json
  {
    "resource_id": "<resource_uuid>",
    "task_id": "<task_uuid>",
    "name": "<filename>",
    "type": "media_parse",
    "status": "uploading",
    "size_bytes": <size>,
    "mime_type": "<declared_mime>",
    "created_at": <unix>
  }
  ```

### 3. 构建并派发 ASR 请求
- **执行方**：Gateway HTTPTaskDispatcher
- **文件**：[`gateway/internal/service/task_dispatcher.go`](../../gateway/internal/service/task_dispatcher.go#L56-L133)
- **说明**：针对 `media_parse` 任务构建 JSON 报文，其中 `audio_url` 为 `minio://<bucket>/<storage_key>`。向 `{AIService.BaseURL}/ai/v1/asr` 发送 `POST`，带 `X-Internal-Key` 头。期望返回 `202 Accepted`。
- **请求体示例**：
  ```json
  {
    "task_id": "<task_uuid>",
    "resource_id": "<resource_uuid>",
    "audio_url": "minio://mkc-resources/<user_uuid>/<resource_uuid>/<filename>",
    "language": "zh",
    "model": "small"
  }
  ```

### 4. 入队 Celery ASR 任务
- **执行方**：AI Service ASR API
- **文件**：[`ai-service/app/main.py`](../../ai-service/app/main.py#L40) 挂载；[`ai-service/app/api/asr.py`](../../ai-service/app/api/asr.py#L39-L67)
- **说明**：`check_internal_key` 优先执行；校验 `AsrTaskRequest`；通过 `_validate_audio_url` 做临时下载/转换健康检查；调用 `run_asr.delay(...)` 入队；返回 202。
- **响应示例**：
  ```json
  {
    "task_id": "<task_uuid>",
    "status": "pending",
    "message": "ASR task queued"
  }
  ```

### 5. 启动 ASR Worker 并置为 running
- **执行方**：Celery Worker `run_asr`
- **文件**：[`ai-service/celery_workers/tasks/asr_task.py`](../../ai-service/celery_workers/tasks/asr_task.py#L34-L62)
- **说明**：`bind=True` 的 Celery 任务基于 `BaseAITask`。校验 `payload` 为 `AsrTaskRequest`；根据 `self.request.retries` 在重试时降级到 `fallback_model='tiny'`；从 `ai.yaml` 构建 `WhisperEngine` 与 `AudioProcessor`；通过 `GatewayProgressReporter` 标记 `running` 状态；调用 `AsrService.process`。
- **入队报文示例**：
  ```json
  {
    "task_id": "<task_uuid>",
    "resource_id": "<resource_uuid>",
    "audio_url": "minio://...",
    "language": "zh",
    "model": "small"
  }
  ```

### 6. 下载并预处理音频
- **执行方**：AsrService
- **文件**：[`ai-service/app/services/asr_service.py`](../../ai-service/app/services/asr_service.py#L67-L110)
- **说明**：从 `minio://` 下载音频到临时文件；转换为 16kHz mono PCM WAV；计算时长；然后开始转写。异常会映射为 `AudioProcessingError` / `AsrProcessingError`。

### 7. 音频转 WAV 并读取时长
- **执行方**：AudioProcessor
- **文件**：[`ai-service/app/services/audio_processor.py`](../../ai-service/app/services/audio_processor.py#L17-L45)
- **说明**：调用 `ffmpeg` 生成 16kHz mono `pcm_s16le` WAV，然后从 WAV 头读取 duration。

### 8. faster-whisper 转写
- **执行方**：WhisperEngine
- **文件**：[`ai-service/app/services/whisper_engine.py`](../../ai-service/app/services/whisper_engine.py#L55-L82)
- **说明**：按配置按需加载模型（默认 `small`），对 WAV 文件执行推理，产出带 `start/end/text/confidence` 的 segment 字典。

### 9. 转写过程中上报进度
- **执行方**：AsrService
- **文件**：[`ai-service/app/services/asr_service.py`](../../ai-service/app/services/asr_service.py#L112-L139)
- **说明**：每个 segment 结束后计算 `progress = min(segment.end / duration * 100, 100)`。当进度变化超过 `progress_interval`（默认 5.0）或达到 100 时，向 Gateway 上报进度。
- **报文示例**：
  ```json
  PATCH /api/v1/internal/tasks/<task_id>/progress
  {"progress": 45, "status": "running"}
  ```

### 10. 发送进度更新到 Gateway
- **执行方**：GatewayProgressReporter
- **文件**：[`ai-service/app/services/gateway_reporter.py`](../../ai-service/app/services/gateway_reporter.py#L31-L35)
- **说明**：`report_progress` 根据 `ai.yaml` 中 `gateway.base_url` 和 `progress_path` 构造 `PATCH` URL，发送 JSON `{progress, status}`，并带 `X-Internal-Key` 头。

### 11. Gateway 接收进度更新
- **执行方**：Gateway InternalTaskHandler
- **文件**：[`gateway/internal/handler/internal_task_handler.go`](../../gateway/internal/handler/internal_task_handler.go#L37-L53)
- **说明**：Handler 绑定 `UpdateProgressRequest`，校验 progress 范围 0-100，调用 `TaskService.UpdateProgress`。

### 12. 持久化进度并广播事件
- **执行方**：Gateway TaskService
- **文件**：[`gateway/internal/service/task_service.go`](../../gateway/internal/service/task_service.go#L257-L277)
- **说明**：`UpdateProgress` 强制任务必须处于 `running` 状态；更新 repository；发布 `eventType='progress'` 的 SSE 事件。

### 13. 上传转写与字幕结果
- **执行方**：AsrService
- **文件**：[`ai-service/app/services/asr_service.py`](../../ai-service/app/services/asr_service.py#L80-L99)
- **说明**：清理 segment，将 `transcript.json` 上传到 MinIO `results/<task_id>/transcript.json`；生成并上传字幕文件；返回 `AsrResult`。
- **结果示例**：
  ```json
  {
    "task_id": "<task_uuid>",
    "resource_id": "<resource_uuid>",
    "segments": [],
    "text": "...",
    "duration": <seconds>,
    "transcript_url": "minio://...",
    "subtitle_url": "minio://..."
  }
  ```

### 14. 任务生命周期钩子上报最终状态
- **执行方**：BaseAITask
- **文件**：[`ai-service/celery_workers/tasks/base.py`](../../ai-service/celery_workers/tasks/base.py#L35-L69)
- **说明**：`on_success` 发送 `completed` 状态与返回字典；`on_retry` 发送 `running`；`on_failure` 发送 `failed` 并带 `error_message`。最多 3 次重试，指数退避。
- **报文示例**：
  ```json
  POST /api/v1/internal/tasks/<task_id>/status
  {
    "status": "completed",
    "result": {"task_id": "...", "transcript_url": "..."},
    "attempt_count": 1
  }
  ```

### 15. 发送状态变更到 Gateway
- **执行方**：GatewayProgressReporter
- **文件**：[`ai-service/app/services/gateway_reporter.py`](../../ai-service/app/services/gateway_reporter.py#L37-L54)
- **说明**：`mark_status` 向 `/api/v1/internal/tasks/{task_id}/status` 发送 `POST`，报文包含 `status/result/error_message/attempt_count`。

### 16. Gateway 接收状态变更
- **执行方**：Gateway InternalTaskHandler
- **文件**：[`gateway/internal/handler/internal_task_handler.go`](../../gateway/internal/handler/internal_task_handler.go#L55-L77)
- **说明**：Handler 绑定 `UpdateStatusRequest`（status 为 `running|completed|failed`），封装为 `InternalStatusUpdate`，调用 `TaskService.ProcessInternalStatusUpdate`。

### 17. 校验状态转换并持久化
- **执行方**：Gateway TaskService
- **文件**：[`gateway/internal/service/task_service.go`](../../gateway/internal/service/task_service.go#L280-L330)
- **说明**：`ProcessInternalStatusUpdate` 强制执行 `canTransition`：
  - `pending -> running`
  - `running -> completed/failed`
  - `failed -> running`
  - 完成时 progress 置 100；失败时置 0；持久化 result/error/attempt_count；发布 SSE 事件 `done` 或 `error`。

### 18. 任务状态常量定义
- **执行方**：Task model
- **文件**：[`gateway/internal/model/task.go`](../../gateway/internal/model/task.go#L30-L42)
- **说明**：定义 `pending/running/completed/failed` 以及 `media_parse/pdf_parse/document_parse` 等类型常量，全链路通用。

### 19. 客户端获取结果
- **执行方**：Gateway ResultHandler
- **文件**：[`gateway/internal/handler/result_handler.go`](../../gateway/internal/handler/result_handler.go#L23-L34)
- **说明**：客户端调用 `GET /api/v1/tasks/{task_id}/result`，Handler 调用 `ResultService.GetResult` 返回摘要 JSON。

### 20. 生成预签名结果 URL
- **执行方**：Gateway ResultService
- **文件**：[`gateway/internal/service/result_service.go`](../../gateway/internal/service/result_service.go#L66-L144)
- **说明**：`GetResult` 校验任务为 `completed`；解析 `task.Result`；提取 `transcript_url/subtitle_url/parsed_url`；校验 bucket 为 `resultsBucket`；通过 `ObjectStorage.PresignedGetURL` 生成预签名 URL。
- **响应示例**：
  ```json
  {
    "task_id": "<task_uuid>",
    "status": "completed",
    "files": {
      "transcript_url": "<presigned>",
      "subtitle_url": "<presigned>"
    },
    "metadata": {}
  }
  ```

### 21. 路由注册
- **执行方**：Gateway Router
- **文件**：[`gateway/internal/router/router.go`](../../gateway/internal/router/router.go#L50-L70)
- **说明**：注册公共路由（`POST /api/v1/files/upload`、`/tasks/:task_id`、`/tasks/:task_id/result`、`/tasks/:task_id/events`）和内部路由 `/api/v1/internal/*`，后者使用 `InternalAuth` 中间件。

---

## 4. 踩坑记录

| 序号 | 问题 | 严重度 | 症状 | 根因 | 影响文件 | 修复 | 预防 |
|------|------|--------|------|------|----------|------|------|
| 1 | MP3 MIME 类型被拒绝（`audio/mp3` vs `audio/mpeg`） | 高 | Flutter/Web 上传 MP3 返回 `400 Bad Request`，提示 `unsupported file type`，文件本身合法 | Gateway 只将 `audio/mpeg` 列入白名单，`compatibleMime` 未识别 `audio/mp3` 也是合法音频类型 | [`gateway/internal/service/file_service.go`](../../gateway/internal/service/file_service.go) | 在 `allowedMimeTypes` 白名单中加入 `"audio/mp3"`，并在 `compatibleMime` 分支中把 `audio/mp3` 视为音频类型 | 保持 MIME 白名单与常见客户端声明同步；用 Flutter、Web、curl 分别测试上传 |
| 2 | 修改代码后 Gateway 未重新编译 | 中 | 源码已改 MIME 白名单，但上传仍然失败，运行中的服务行为与代码不一致 | 编译产物 `bin/server` 比源码旧，运行时仍是旧二进制 | `gateway/bin/server` | 重新编译 `go build -o bin/server`，确认二进制时间戳比最新源码新 | 使用 Makefile/启动脚本先编译再启动；启动健康检查返回二进制构建时间 |
| 3 | 端口 8080 被旧 Gateway 进程占用 | 中 | 新二进制启动报 `address already in use`，或请求仍命中旧二进制 | 旧进程未释放 8080 端口，新服务无法接管 | [`gateway/cmd/server/main.go`](../../gateway/cmd/server/main.go) | `lsof -i :8080` 找到旧 PID 后 `kill <PID>`，再启动新二进制 | 实现优雅关闭以响应 SIGTERM；开发分支/会话使用独立端口，或启动前检测端口 |
| 4 | AI Service 缺少 ffmpeg | 高 | ASR 任务在预处理阶段失败，日志报 `ffmpeg not found` / `FileNotFoundError` | `audio_processor` 使用 `ffmpeg-python` 调用系统 `ffmpeg`，但环境未安装或不在 PATH | [`ai-service/app/services/audio_processor.py`](../../ai-service/app/services/audio_processor.py) | 在宿主机安装 ffmpeg（如 macOS `brew install ffmpeg`），并确保 Celery Worker 进程 PATH 可访问 | 服务启动时检查 ffmpeg 存在；README 写明依赖；Docker 镜像内预装 ffmpeg |
| 5 | Python 虚拟环境损坏（3.12 vs 3.13 混用） | 中 | 出现 `ModuleNotFoundError`，或包为 3.12 安装却被 3.13 导入 | `.venv` 中 `python`/`python3` 指向 3.12，而系统为 3.13，且存在独立 `python3.13` 软链，导致导入路径混乱 | `ai-service/.venv/bin/python`<br>`ai-service/.venv/bin/python3` | 用目标 Python 重建 venv：`python3.13 -m venv .venv`，然后从 `requirements.txt` 重装依赖 | 在 README 与 `pyproject.toml` 中固定 Python 版本；使用 setup 脚本验证 venv 解释器版本 |
| 6 | Whisper 模型未下载 / `model_dir` 不可写 | 高 | `faster-whisper` 报模型路径错误或无法下载，所有 ASR 任务立即失败 | 配置 `/models/whisper` 目录不存在或本地不可写 | [`ai-service/config/ai.yaml`](../../ai-service/config/ai.yaml)<br>[`ai-service/app/services/whisper_engine.py`](../../ai-service/app/services/whisper_engine.py) | 将 `asr.model_dir` 改为本地可写目录，如 `ai-service/models/whisper`，并确保目录存在 | 使用环境相关路径或运行时展开用户可写目录；启动时检查模型目录存在且可写 |
| 7 | Celery 任务重试签名与 `bind=True` 冲突 | 高 | 重试时出现参数绑定错误，或降级模型未生效；任务首次失败后挂死/异常退出 | `run_asr` 同时启用 `bind=True` 和手动 `self.retry(args=[...])`，与 `BaseAITask.autoretry_for` 冲突 | [`ai-service/celery_workers/tasks/asr_task.py`](../../ai-service/celery_workers/tasks/asr_task.py) | 移除手动 `self.retry(...)`，依赖 `BaseAITask.autoretry_for`/`on_retry`/`on_failure`；通过 `self.request.retries` 判断降级模型 | 理解 `bind=True` 语义：不要传 `self` 进 retry args；不要混用自动重试与手动重试；对 Celery 重试逻辑做单元测试 |
| 8 | Gateway 进度上报误用 POST 而非 PATCH | 高 | UI 进度始终 0%，AI Service 日志报 404/405 | `GatewayProgressReporter` 向进度端点发送 `POST`，但 Gateway 路由为 `PATCH /api/v1/internal/tasks/:task_id/progress` | [`ai-service/app/services/gateway_reporter.py`](../../ai-service/app/services/gateway_reporter.py) | 为 `report_progress` 增加独立 `_patch` 方法，调用 `PATCH`；`_post` 仅用于状态变更 | 让 HTTP 客户端代码与路由定义保持一致；对 reporter 做单元测试断言方法 |
| 9 | Celery 生命周期钩子使用 Celery 内部 UUID 而非业务 task_id | 关键 | 状态更新命中不存在的 task ID，Gateway 返回 404，UI 任务卡在 pending 或结果丢失 | `BaseAITask` 的钩子参数 `task_id` 是 Celery 内部 UUID，却被直接当作业务 task_id 发给 Gateway | [`ai-service/celery_workers/tasks/base.py`](../../ai-service/celery_workers/tasks/base.py) | 新增 `_business_task_id` 辅助函数：从第一个位置参数或 `kwargs["task_id"]` 提取业务 ID，并在 `on_success/on_retry/on_failure` 中使用 | 永远不要用 Celery 内部 task_id 作为业务标识；所有 Gateway 状态更新必须从任务自身参数解析 |
| 10 | AsrService 与 BaseAITask 重复上报状态 | 中 | Gateway 收到多条 completed/failed/running 事件，状态机竞争、任务历史混乱 | `AsrService.process()` 内主动发送状态变更，而 `BaseAITask` 钩子也发送同样的状态变更 | [`ai-service/app/services/asr_service.py`](../../ai-service/app/services/asr_service.py)<br>[`ai-service/celery_workers/tasks/base.py`](../../ai-service/celery_workers/tasks/base.py) | 移除 `AsrService.process()` 中的状态变更（running/completed/failed），只保留进度更新；由 `BaseAITask` 钩子统一负责状态变更 | 明确单一职责：服务层只报进度，生命周期钩子管状态；避免多层级重复上报 |

---

## 5. 验证命令

> 以下命令均使用占位符（如 `$GATEWAY_BASE_URL`、`$TOKEN`、`$TASK_ID`），请替换为环境变量或实际值。不要直接写入任何真实 secret。

### 5.1 环境快速检查

```bash
# 1. Gateway 是否已监听 8080
lsof -i :8080

# 2. Gateway 二进制时间戳是否比源码新
stat /Users/zhushuangquan/Downloads/MKC/gateway/bin/server
ls -lt /Users/zhushuangquan/Downloads/MKC/gateway/bin/server /Users/zhushuangquan/Downloads/MKC/gateway/internal/service/*.go | head

# 3. ffmpeg 是否可用（AI Service 宿主机）
which ffmpeg && ffmpeg -version | head -n 1

# 4. Python 虚拟环境版本是否一致（AI Service）
cd /Users/zhushuangquan/Downloads/MKC/ai-service
.venv/bin/python --version
.venv/bin/python3 --version
.venv/bin/python3.13 --version 2>/dev/null || true

# 5. Celery Worker 是否在线
cd /Users/zhushuangquan/Downloads/MKC/ai-service
celery -A app.celery inspect ping

# 6. MinIO 桶是否存在
mc ls local/mkc-resources 2>/dev/null || echo "check minio alias"
```

### 5.2 上传文件

```bash
export GATEWAY_BASE_URL="http://localhost:8080"
export TOKEN="$YOUR_USER_TOKEN"       # 或登录后获取的 JWT
export AUDIO_FILE="/path/to/audio.mp3"

curl -sS -X POST "$GATEWAY_BASE_URL/api/v1/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$AUDIO_FILE" \
  -F "type=media_parse" \
  -F "language=zh" \
  -F "model=small" \
  | tee /tmp/upload_response.json

# 提取 task_id
export TASK_ID=$(jq -r '.task_id' /tmp/upload_response.json)
echo "TASK_ID=$TASK_ID"
```

### 5.3 轮询任务状态（SSE 之外的可选方式）

```bash
# 每 3 秒查询一次，直到状态为 completed 或 failed
while true; do
  STATUS=$(curl -sS "$GATEWAY_BASE_URL/api/v1/tasks/$TASK_ID" \
    -H "Authorization: Bearer $TOKEN" \
    | jq -r '.status')
  echo "$(date '+%H:%M:%S') status=$STATUS"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then break; fi
  sleep 3
done
```

### 5.4 获取结果

```bash
curl -sS "$GATEWAY_BASE_URL/api/v1/tasks/$TASK_ID/result" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# 仅下载 transcript
TRANSCRIPT_URL=$(curl -sS "$GATEWAY_BASE_URL/api/v1/tasks/$TASK_ID/result" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.files.transcript_url')
curl -sS "$TRANSCRIPT_URL" -o /tmp/transcript.json
```

### 5.5 查看 Celery 任务队列

```bash
cd /Users/zhushuangquan/Downloads/MKC/ai-service
source .venv/bin/activate

# 查看已注册任务列表
celery -A app.celery inspect registered

# 查看当前正在执行的任务
celery -A app.celery inspect active

# 查看任务统计
celery -A app.celery inspect stats
```

### 5.6 查看关键日志

```bash
# Gateway
tail -f /Users/zhushuangquan/Downloads/MKC/gateway/logs/*.log

# AI Service / Celery
tail -f /Users/zhushuangquan/Downloads/MKC/ai-service/logs/celery.log
```

---

## 6. 未提交改动清单

> 以下清单基于当前工作目录 `git status` 和 `git diff --stat`，在提交/合并前请逐项确认。

| 文件 | Git 状态 | 改动说明 | 对应踩坑 |
|------|----------|----------|----------|
| [`ai-service/app/services/asr_service.py`](../../ai-service/app/services/asr_service.py) | 修改 | 移除 `AsrService.process()` 中手动发送 `running`/`completed`/`failed` 状态的逻辑，仅保留进度更新 | 踩坑 #10 |
| [`ai-service/app/services/gateway_reporter.py`](../../ai-service/app/services/gateway_reporter.py) | 修改 | 新增 `_patch` 方法供 `report_progress` 使用，将进度上报改为 `PATCH`；`mark_status` 保持 `POST` | 踩坑 #8 |
| [`ai-service/celery_workers/tasks/asr_task.py`](../../ai-service/celery_workers/tasks/asr_task.py) | 修改 | 移除手动 `self.retry(...)` 调用；依赖 `BaseAITask.autoretry_for`；通过 `self.request.retries` 切换降级模型 | 踩坑 #7 |
| [`ai-service/celery_workers/tasks/base.py`](../../ai-service/celery_workers/tasks/base.py) | 修改 | 新增 `_business_task_id` 辅助函数，从任务参数解析业务 `task_id`，用于 `on_success/on_retry/on_failure` | 踩坑 #9 |
| [`ai-service/config/ai.yaml`](../../ai-service/config/ai.yaml) | 修改 | 将 `asr.model_dir` 改为本地可写路径 | 踩坑 #6 |
| [`gateway/internal/service/file_service.go`](../../gateway/internal/service/file_service.go) | 修改 | 将 `audio/mp3` 加入 MIME 白名单并兼容识别 | 踩坑 #1 |
| [`gateway/internal/service/file_service_edge_test.go`](../../gateway/internal/service/file_service_edge_test.go) | 修改 | 新增边界测试 | 踩坑 #1 |
| [`gateway/internal/service/file_service_test.go`](../../gateway/internal/service/file_service_test.go) | 修改 | 新增 MIME 白名单相关单元测试 | 踩坑 #1 |
| `resources/` | 未跟踪 | 本地上传测试文件，**不应提交**；请确认是否已加入 `.gitignore` | - |

### 统计

```text
 8 files changed, 74 insertions(+), 49 deletions(-)
```

---

## 7. 后续检查项

在提交、合并或部署前，请确认以下检查项：

- [ ] **代码层面**
  - [ ] `audio/mp3` 与 `audio/mpeg` 均被 Gateway 接受
  - [ ] `GatewayProgressReporter` 进度上报使用 `PATCH`，状态上报使用 `POST`
  - [ ] `BaseAITask` 钩子使用业务 `task_id` 而非 Celery UUID
  - [ ] `AsrService` 不直接发送状态变更，只上报进度
  - [ ] `run_asr` 不再手动调用 `self.retry(...)`
  - [ ] `ai.yaml` 中 `model_dir` 为本地可写路径
- [ ] **构建与运行环境**
  - [ ] Gateway 已重新编译，二进制时间戳新于源码
  - [ ] 8080 端口未被旧 Gateway 进程占用
  - [ ] AI Service 所在环境已安装 ffmpeg 且 PATH 可达
  - [ ] Python 虚拟环境版本一致（目标 3.13），依赖已重装
- [ ] **测试验证**
  - [ ] 单元测试通过：`gateway/internal/service/file_service_test.go` 与 `file_service_edge_test.go`
  - [ ] 使用 curl 完整跑通一次上传→轮询→获取结果流程
  - [ ] 触发一次失败场景（如删除模型目录），确认重试与降级模型逻辑正常
  - [ ] 进度条能从 0% 正常推进到 100%
- [ ] **安全与配置**
  - [ ] 未提交任何真实 secret（仅使用环境变量名如 `X_INTERNAL_KEY`、`MINIO_ENDPOINT`）
  - [ ] `resources/` 未误提交，已在 `.gitignore` 中忽略
  - [ ] 环境变量与 `ai.yaml` 中 Gateway / MinIO 端点配置正确
- [ ] **文档同步**
  - [ ] README 中已更新 ffmpeg、Python 版本、本地模型目录说明
  - [ ] 本 runbook 与最新代码保持一致

---

*最后更新：2026-07-10*
