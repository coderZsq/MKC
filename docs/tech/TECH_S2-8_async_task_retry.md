# 技术文档：[S2-8] 转录/解析任务异步执行与失败重试

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：后端/AI 工程师
> 关联 PRD：[../prd/PRD_S2-8_async_task_retry.md](../prd/PRD_S2-8_async_task_retry.md)

---

## 1. 文档目标

定义 ASR/PDF 解析任务的异步执行与重试机制：Gateway 任务分派、Celery Worker 执行、自动重试、手动重试、状态同步与测试策略。

---

## 2. 技术栈

- Go 1.22+ / Gin 1.10.x
- Python 3.11+
- Celery 5.4+ + Redis 7.x
- GORM 1.25.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/tasks` | Bearer JWT | 创建任务（已存在 S1-5） |
| POST | `/api/v1/tasks/{task_id}/retry` | Bearer JWT | 手动重试失败任务 |
| PATCH | `/api/v1/internal/tasks/{task_id}/progress` | Internal API Key | AI Service 上报进度 |

### 请求示例

```text
POST /api/v1/tasks/01922b9c-.../retry
Authorization: Bearer <access_token>
```

### 响应示例

```json
{
  "success": true,
  "data": {
    "task_id": "01922b9c-...",
    "status": "pending",
    "attempt_count": 0
  }
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 404 | TASK_NOT_FOUND | 任务不存在或无权访问 |
| 400 | TASK_NOT_RETRYABLE | 任务状态不允许重试 |
| 429 | RETRY_TOO_FREQUENT | 重试过于频繁 |
| 500 | DISPATCH_FAILED | 任务派发失败 |

---

## 4. 配置

新增 `config/gateway.yaml`：

```yaml
task:
  max_retries: 3
  retry_delays: [60, 300, 900]
  retry_cooldown: 300  # 手动重试冷却时间（秒）
  dispatch_timeout: 10
```

新增 `config/ai.yaml`：

```yaml
celery:
  broker_url: redis://redis:6379/0
  result_backend: redis://redis:6379/0
  task_serializer: json
  result_serializer: json
  accept_content: ["json"]
  task_acks_late: true
  task_reject_on_worker_lost: true
  task_track_started: true
```

---

## 5. 模块设计

### 5.1 Gateway

- `TaskDispatcher`: 根据任务类型分派到 Celery
- `TaskRetryHandler`: 手动重试入口
- `TaskService`: 状态校验与重试逻辑

### 5.2 AI Service

- `BaseCeleryTask`: 状态上报与异常捕获基类
- `AsrTask`: ASR 任务
- `PdfParseTask`: PDF 解析任务
- `ProgressReporter`: 上报进度到 Gateway

---

## 6. 关键代码实现

### 6.1 Celery 任务基类

```python
from celery import Task
from celery.exceptions import MaxRetriesExceededError

class BaseAITask(Task):
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 3600
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # 上报失败状态到 Gateway
        report_status(task_id, "failed", str(exc))
```

### 6.2 ASR Celery 任务

```python
@app.task(bind=True, base=BaseAITask)
def run_asr(self, task_id: str, payload: dict):
    report_status(task_id, "running")
    try:
        result = asr_service.process(payload)
        result_storage.save(task_id, result)
        report_status(task_id, "completed", progress=100)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

### 6.3 Gateway 手动重试

```go
func (s *taskService) Retry(ctx context.Context, userID uint64, taskID string) error {
    task, err := s.repo.GetByID(ctx, taskID)
    if err != nil || task.UserID != userID {
        return ErrTaskNotFound
    }
    if task.Status != "failed" && task.Status != "completed" {
        return ErrTaskNotRetryable
    }
    if time.Since(task.UpdatedAt) < s.retryCooldown {
        return ErrRetryTooFrequent
    }
    task.AttemptCount = 0
    task.ErrorMessage = ""
    task.Status = "pending"
    if err := s.repo.Update(ctx, task); err != nil {
        return err
    }
    return s.dispatcher.Dispatch(ctx, task)
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 任务不存在或无权访问 | 404 | TASK_NOT_FOUND | 任务不存在 |
| 任务非失败/完成状态 | 400 | TASK_NOT_RETRYABLE | 当前状态不可重试 |
| 重试过于频繁 | 429 | RETRY_TOO_FREQUENT | 请稍后重试 |
| 任务派发失败 | 500 | DISPATCH_FAILED | 任务派发失败 |
| Celery Worker 未启动 | 503 | WORKER_UNAVAILABLE | 处理服务不可用 |

---

## 8. Web 端适配要点

- Web 端 Flutter 任务中心为 failed 任务显示“重试”按钮
- 重试成功后刷新任务状态，重新订阅 SSE 进度
- 完成状态的任务也允许手动重试（重新解析）

---

## 9. 测试策略

- **Gateway 单元测试**：重试权限、状态校验、冷却时间
- **Gateway 集成测试**：调用 retry → 任务重置 → Celery 收到任务
- **AI Service 单元测试**：Celery 任务异常重试、最大重试后失败
- **E2E 测试**：上传文件 → 模拟失败 → 手动重试 → 成功

---

## 10. 检查清单

- [ ] Gateway 任务分派器
- [ ] Gateway 手动重试接口
- [ ] Celery 任务基类与重试策略
- [ ] AI Service 进度上报
- [ ] 任务状态机校验
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
