# 技术文档：[S1-5] 任务创建与状态查询 API 设计

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 级别：后端工程师  
> 关联 PRD：[PRD_S1-5_task_status_api.md](../prd/PRD_S1-5_task_status_api.md)

---

## 1. 文档目标

定义 Gateway 任务管理模块的接口契约、状态机、数据访问、模块划分与关键代码实现，为 S1-5 编码提供可直接落地的蓝图。

---

## 2. 技术栈

- Go 1.22+
- Gin 1.10.x
- GORM 1.25.x
- MySQL 8

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api/v1/tasks` | Bearer JWT | 列出当前用户任务 |
| GET | `/api/v1/tasks/{task_id}` | Bearer JWT | 查询任务详情 |
| POST | `/api/v1/tasks` | Bearer JWT | 为已有资源创建任务 |

### 3.1 请求/响应示例

**GET /api/v1/tasks**

```text
GET /api/v1/tasks?page=1&limit=20
Authorization: Bearer <access_token>
```

```json
{
  "success": true,
  "data": [
    {
      "task_id": "01922b9c-...",
      "resource_id": "01922b9a-...",
      "type": "media_parse",
      "status": "pending",
      "progress": 0,
      "created_at": "2026-07-08T10:00:00Z",
      "updated_at": "2026-07-08T10:00:00Z"
    }
  ],
  "error": null,
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "request_id": "..."
  }
}
```

**GET /api/v1/tasks/{task_id}**

```json
{
  "success": true,
  "data": {
    "task_id": "01922b9c-...",
    "resource_id": "01922b9a-...",
    "user_id": "01922b9b-...",
    "type": "media_parse",
    "status": "running",
    "progress": 35,
    "result": null,
    "error_message": null,
    "started_at": "2026-07-08T10:01:00Z",
    "completed_at": null,
    "created_at": "2026-07-08T10:00:00Z",
    "updated_at": "2026-07-08T10:01:30Z"
  },
  "error": null,
  "meta": { "request_id": "..." }
}
```

**POST /api/v1/tasks**

```json
// Request
{
  "resource_id": "01922b9a-...",
  "type": "media_parse"
}

// Response 200
{
  "success": true,
  "data": {
    "task_id": "01922b9c-...",
    "resource_id": "01922b9a-...",
    "type": "media_parse",
    "status": "pending",
    "progress": 0,
    "created_at": "2026-07-08T10:00:00Z"
  }
}
```

---

## 4. 数据模型

复用 `gateway/internal/model/task.go`：

```go
type Task struct {
    ID           uint64
    UUID         string
    ResourceID   uint64
    UserID       uint64
    Type         string
    Status       string
    Progress     uint8
    Result       json.RawMessage
    ErrorMessage string
    StartedAt    *time.Time
    CompletedAt  *time.Time
    RetryCount   uint8
    CreatedAt    time.Time
    UpdatedAt    time.Time
}
```

状态常量：

```go
const (
    TaskStatusPending   = "pending"
    TaskStatusRunning   = "running"
    TaskStatusCompleted = "completed"
    TaskStatusFailed    = "failed"
)
```

---

## 5. 模块设计

### 5.1 Repository 层

```go
type TaskRepository interface {
    Create(ctx context.Context, t *model.Task) error
    GetByUUID(ctx context.Context, uuid string) (*model.Task, error)
    GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error)
    ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error)
    UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error
    UpdateProgress(ctx context.Context, id uint64, progress uint8) error
}
```

### 5.2 Service 层

```go
type TaskService interface {
    Create(ctx context.Context, userID uint64, req CreateTaskRequest) (*TaskDTO, error)
    Get(ctx context.Context, userID uint64, taskUUID string) (*TaskDTO, error)
    List(ctx context.Context, userID uint64, page, limit int) (*ListTasksResult, error)
    UpdateProgress(ctx context.Context, taskUUID string, progress uint8) error
    MarkRunning(ctx context.Context, taskUUID string) error
    MarkCompleted(ctx context.Context, taskUUID string, result json.RawMessage) error
    MarkFailed(ctx context.Context, taskUUID string, errMsg string) error
}
```

状态机校验：

```go
var allowedTransitions = map[string][]string{
    TaskStatusPending:   {TaskStatusRunning},
    TaskStatusRunning:   {TaskStatusCompleted, TaskStatusFailed},
    TaskStatusCompleted: {},
    TaskStatusFailed:    {},
}

func canTransition(from, to string) bool {
    for _, s := range allowedTransitions[from] {
        if s == to {
            return true
        }
    }
    return false
}
```

### 5.3 Handler 层

```go
func (h *TaskHandler) List(c *gin.Context) {
    userID := c.GetUint64("user_id")
    page := parsePage(c.DefaultQuery("page", "1"))
    limit := parseLimit(c.DefaultQuery("limit", "20"), 100)

    result, err := h.svc.List(c.Request.Context(), userID, page, limit)
    if err != nil {
        handleServiceError(c, err)
        return
    }
    response.OKWithMeta(c, result.Tasks, response.Meta{Page: page, Limit: limit, Total: result.Total})
}
```

---

## 6. 关键代码实现

### 6.1 创建任务

```go
func (s *taskService) Create(ctx context.Context, userID uint64, req CreateTaskRequest) (*TaskDTO, error) {
    resource, err := s.resourceRepo.GetByUUIDAndUserID(ctx, req.ResourceID, userID)
    if err != nil {
        return nil, err
    }

    taskType := req.Type
    if taskType == "" {
        taskType = resource.Type
    }

    task := &model.Task{
        UUID:       uuid.NewString(),
        ResourceID: resource.ID,
        UserID:     userID,
        Type:       taskType,
        Status:     model.TaskStatusPending,
        Progress:   0,
    }
    if err := s.taskRepo.Create(ctx, task); err != nil {
        return nil, fmt.Errorf("create task: %w", err)
    }
    return toTaskDTO(task), nil
}
```

### 6.2 更新进度

```go
func (s *taskService) UpdateProgress(ctx context.Context, taskUUID string, progress uint8) error {
    if progress > 100 {
        return apperrors.BadRequest("progress must be 0-100")
    }
    task, err := s.taskRepo.GetByUUID(ctx, taskUUID)
    if err != nil {
        return err
    }
    if task.Status != model.TaskStatusRunning {
        return apperrors.BadRequest("task is not running")
    }
    return s.taskRepo.UpdateProgress(ctx, task.ID, progress)
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 分页参数非法 | 400 | VALIDATION_ERROR | 分页参数错误 |
| resource 不存在或不属于当前用户 | 404 | NOT_FOUND | 资源不存在 |
| task 不存在或不属于当前用户 | 404 | NOT_FOUND | 任务不存在 |
| 状态转换非法 | 400 | INVALID_STATE_TRANSITION | 非法的状态变更 |
| 进度超出 0-100 | 400 | VALIDATION_ERROR | 进度值非法 |
| 未认证 | 401 | UNAUTHORIZED | 访问令牌无效 |
| 内部错误 | 500 | INTERNAL_ERROR | 服务器内部错误 |

---

## 8. Web 端适配要点

- Gateway 任务列表/详情/创建接口需启用 CORS：允许 Flutter Web 启动域名、允许 `Authorization` 头或 credentials。
- 分页响应的 `meta` 字段用于 Web 端加载更多与总页数展示；列表接口返回 `resource_name` 以减少前端二次请求。
- Web 端 Widget/集成测试使用 `flutter test --platform chrome` 与 ChromeDriver。

---

## 9. 测试策略

- **单元测试**：状态机转换、分页参数校验、DTO 映射
- **集成测试**：repository + MySQL，验证 CRUD、分页、权限隔离
- **接口测试**：httptest 模拟 401/404/200/状态转换

---

## 10. 检查清单

- [ ] `TaskHandler` List/Get/Create 接口实现
- [ ] `TaskService` 业务逻辑与状态机实现
- [ ] `TaskRepository` 数据访问实现
- [ ] 任务状态常量与转换校验
- [ ] 分页与 meta 封装
- [ ] 用户权限隔离（404 统一）
- [ ] 单元/集成测试覆盖率 80%+
- [ ] OpenAPI 文档同步更新
