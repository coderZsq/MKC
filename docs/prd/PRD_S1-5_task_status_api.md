# PRD：[S1-5] 实现任务创建与状态查询 API

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 关联文档：[PRD_S1-3_file_upload_api.md](./PRD_S1-3_file_upload_api.md)、[TECH_S1-5_task_status_api.md](../tech/TECH_S1-5_task_status_api.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S1-5 |
| **任务名称** | 实现任务创建与状态查询 API |
| **所属史诗** | E3 任务管理 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S1-3 文件上传 API、S0-4 数据库 Schema |
| **目标 Sprint** | Sprint 1 |

---

## 描述

作为用户，我需要查看已上传文件对应的 AI 处理任务状态，并能在必要时手动创建任务。本任务在 Gateway 实现任务生命周期管理 API：创建任务、查询任务详情、分页列出任务，并定义清晰的状态机。

---

## 验收标准（AC）

- [ ] **AC-1** `GET /api/v1/tasks` 返回当前用户的任务列表，支持分页（page/limit）
- [ ] **AC-2** `GET /api/v1/tasks/{task_id}` 返回指定任务详情，且用户只能查看自己的任务
- [ ] **AC-3** `POST /api/v1/tasks` 允许为已有资源创建新任务（用于重新解析）
- [ ] **AC-4** 任务状态机：`pending` → `running` → `completed`/`failed`
- [ ] **AC-5** 状态变更时更新 `progress`（0-100）、`started_at`、`completed_at`
- [ ] **AC-6** 错误信息写入 `error_message`，不暴露内部堆栈
- [ ] **AC-7** 所有端点需 JWT 认证
- [ ] **AC-8** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
gateway/
├── internal/
│   ├── handler/
│   │   └── task_handler.go
│   ├── service/
│   │   └── task_service.go
│   ├── repository/
│   │   └── task_repository.go
│   ├── model/
│   │   └── task.go             # 已存在，复用
│   └── dto/
│       └── task_dto.go
└── pkg/errors/errors.go        # 已存在，复用
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| gin-gonic/gin | v1.10.x | HTTP 路由与参数绑定 |
| gorm.io/gorm | v1.25.x | 任务数据访问 |
| google/uuid | v1.x | task UUID |

---

## 技术要点

### 状态机

```
pending  --start-->  running  --finish-->  completed
                       |
                       +--fail--> failed
```

- 只有 AI Service 或内部 worker 可以调用状态推进接口
- 状态变更需校验前置状态，非法转换返回 400

### 权限

- 普通用户只能查询/创建属于自己的任务
- 任务记录中 `user_id` 来自当前登录用户
- 访问不属于自己的任务统一返回 404，避免枚举

### 分页

- 默认 `page=1`、`limit=20`
- 最大 `limit=100`
- 返回 envelope 中 `meta` 包含 `page`、`limit`、`total`

### 任务类型

- `media_parse`：音视频解析
- `pdf_parse`：PDF 解析
- `document_parse`：通用文档解析
- 未来可扩展 `summarize`、`qa` 等

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| AI Service 未就绪导致状态停留在 pending | 用户体验 | Sprint 1 允许手动/模拟推进状态；真实消费由 S1-7 后补充 |
| 任务表数据量大 | 列表慢 | 使用数据库索引（idx_tasks_user_status、idx_tasks_status_created） |

---

## Web 端适配

- Web 端 Flutter 任务中心调用 `GET /api/v1/tasks` 与 `GET /api/v1/tasks/{task_id}`，Gateway 需配置 CORS：允许 Flutter Web 启动域名、允许 `Authorization` 头或 credentials。
- 分页响应 envelope 中的 `meta` 字段用于 Web 端列表加载更多与总页数展示。
- Web 端 Widget/集成测试使用 `flutter test --platform chrome` 与 ChromeDriver 验证列表、分页与详情。

---

## 备注

- 任务创建默认从 resource 记录推断 type；若不明确则默认 `document_parse`
- 同一资源可创建多个任务（重新解析），但 Sprint 1 不实现并发去重
- 任务详情中 `result` 字段在 Sprint 1 为空对象；内容填充后续实现
