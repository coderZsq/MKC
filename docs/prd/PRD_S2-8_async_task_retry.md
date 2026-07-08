# PRD：[S2-8] 转录/解析任务异步执行与失败重试

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[PRD_S1-5_task_status_api.md](./PRD_S1-5_task_status_api.md)、[PRD_S2-1_faster_whisper_asr.md](./PRD_S2-1_faster_whisper_asr.md)、[PRD_S2-4_pdf_text_extraction.md](./PRD_S2-4_pdf_text_extraction.md)、[PRD_S2-6_result_storage.md](./PRD_S2-6_result_storage.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-8 |
| **任务名称** | 转录/解析任务异步执行与失败重试 |
| **所属史诗** | E3 任务进度 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S1-5 任务状态 API、S2-1 ASR、S2-4 PDF 解析、S2-6 结果存储 |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望上传的音频/文档能被后台自动处理，并在失败时支持手动重试。本任务在 Gateway 与 AI Service 之间建立 Celery 异步任务链路，实现任务调度、状态同步、指数退避重试与手动重试入口。

---

## 验收标准（AC）

- [ ] **AC-1** Gateway 创建任务时，根据资源类型（MP3/PDF）自动分派 ASR 或 PDF 解析 Celery 任务
- [ ] **AC-2** Celery Worker 执行 ASR/PDF 解析任务，并实时上报进度
- [ ] **AC-3** 任务失败时自动重试，使用指数退避（如 1min / 5min / 15min / 1h）
- [ ] **AC-4** 达到最大重试次数后任务标记为 failed，并记录错误信息
- [ ] **AC-5** Gateway 提供 `POST /api/v1/tasks/{task_id}/retry` 手动重试接口
- [ ] **AC-6** 手动重试时重置尝试次数并重新派发任务
- [ ] **AC-7** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
gateway/
├── internal/
│   ├── handler/
│   │   └── task_handler.go          # retry 端点
│   ├── service/
│   │   ├── task_service.go
│   │   └── task_dispatcher.go       # 任务分派器
│   └── worker/
│       └── celery_client.go         # 发送任务到 Celery

ai-service/
├── app/
│   ├── tasks/
│   │   ├── asr_task.py
│   │   ├── pdf_parse_task.py
│   │   └── base_task.py             # 重试与状态上报基类
│   └── services/
│       └── progress_reporter.py     # 进度上报
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Celery | 5.4.x | 异步任务队列与重试 |
| Redis | 7.x | Celery Broker 与 Backend |
| amqp / redis-py | - | 消息队列客户端 |
| Go Celery 客户端 | 或 HTTP 回调 | Gateway 派发任务 |

---

## 技术要点

### 任务状态流转

```
pending --dispatch--> running --success--> completed
  |                        |
  +--retry--(exponential)--+--max-retries--> failed
```

### 指数退避配置

```yaml
celery:
  task_acks_late: true
  task_reject_on_worker_lost: true
  task_retry:
    max_retries: 3
    countdown: 60
    backoff: true
    backoff_max: 3600
```

### 任务分派策略

| 资源类型 | 任务类型 | Celery Task |
|---|---|---|
| MP3 | media_parse | ai.tasks.asr_task.run_asr |
| PDF | pdf_parse | ai.tasks.pdf_parse_task.run_pdf_parse |
| 其他 | document_parse | 后续扩展 |

### 手动重试

1. 用户调用 `POST /api/v1/tasks/{task_id}/retry`
2. Gateway 校验任务状态为 failed 或用户权限
3. 重置 `attempt_count` 与 `error_message`
4. 重新分派 Celery 任务

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Celery Worker 崩溃导致任务丢失 | 任务卡住 | 配置 acks_late + reject_on_worker_lost |
| Redis 不可用 | 任务无法派发 | 启动时检测 Redis，失败返回 503 |
| 重试风暴 | 资源耗尽 | 指数退避 + 最大重试次数 |
| 手动重试被滥用 | 资源浪费 | 限制同一任务重试频率 |

---

## Web 端适配

Web 端 Flutter 任务中心展示失败任务，并提供“重试”按钮。点击后调用 `POST /api/v1/tasks/{task_id}/retry`，成功后刷新任务状态。

---

## 备注

- 任务分派器应支持未来扩展更多任务类型（summarize、qa）
- 重试次数与历史需持久化到 task 表
- 手动重试成功后清理旧错误信息
