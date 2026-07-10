# 技术文档：[S3-8] 会话与消息持久化

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：后端工程师
> 关联 PRD：[../prd/PRD_S3-8_conversation_persistence.md](../prd/PRD_S3-8_conversation_persistence.md)

---

## 1. 文档目标

定义 Gateway 中会话与消息持久化模块的技术实现：数据库 schema、数据模型、REST API、上下文窗口管理与测试策略。

---

## 2. 技术栈

- Go 1.22+
- Gin 1.10.x
- GORM 1.25.x
- MySQL 8.0+

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/conversations` | Bearer JWT | 创建会话 |
| GET | `/api/v1/conversations` | Bearer JWT | 列出会话 |
| GET | `/api/v1/conversations/{id}` | Bearer JWT | 会话详情 |
| DELETE | `/api/v1/conversations/{id}` | Bearer JWT | 删除会话 |
| GET | `/api/v1/conversations/{id}/messages` | Bearer JWT | 分页消息 |
| POST | `/api/v1/conversations/{id}/messages` | Bearer JWT | 创建消息 |

### 请求/响应示例

```json
POST /api/v1/conversations
{
  "title": "项目复盘",
  "resource_ids": ["res-1"]
}
```

```json
GET /api/v1/conversations/{id}/messages?page=1&limit=20
{
  "items": [...],
  "total": 45,
  "page": 1,
  "limit": 20
}
```

---

## 4. 配置

新增 `config/gateway.yaml`：

```yaml
conversation:
  default_title: "新会话"
  max_context_messages: 20
  max_context_tokens: 4096
```

---

## 5. 模块设计

### 5.1 Conversation 模型

```go
type Conversation struct {
    ID          string    `gorm:"primaryKey;type:varchar(36)"`
    UserID      uint64    `gorm:"index"`
    Title       string    `gorm:"type:varchar(255)"`
    ResourceIDs string    `gorm:"type:json"`
    CreatedAt   time.Time
    UpdatedAt   time.Time
}
```

### 5.2 Message 模型

```go
type Message struct {
    ID             string `gorm:"primaryKey;type:varchar(36)"`
    ConversationID string `gorm:"index;type:varchar(36)"`
    Role           string `gorm:"type:varchar(16)"`
    Content        string `gorm:"type:text"`
    Citations      string `gorm:"type:json"`
    Model          string
    TokenUsage     int
    CreatedAt      time.Time
}
```

### 5.3 ConversationService

```go
type ConversationService interface {
    Create(ctx context.Context, userID uint64, req CreateConversationRequest) (*Conversation, error)
    List(ctx context.Context, userID uint64, page, limit int) ([]Conversation, int64, error)
    Get(ctx context.Context, userID uint64, id string) (*Conversation, error)
    Delete(ctx context.Context, userID uint64, id string) error
}
```

### 5.4 ContextWindowService

```go
type ContextWindowService interface {
    BuildMessages(ctx context.Context, conversationID string, question string, maxTokens int) ([]Message, error)
}
```

---

## 6. 关键代码实现

### 6.1 上下文窗口截断

```go
func (s *contextWindowService) BuildMessages(ctx context.Context, conversationID string, question string, maxTokens int) ([]Message, error) {
    messages, err := s.msgRepo.ListByConversation(ctx, conversationID, 0, s.maxContextMessages)
    if err != nil {
        return nil, err
    }
    var selected []Message
    total := estimateTokens(question)
    for i := len(messages) - 1; i >= 0; i-- {
        tokens := estimateTokens(messages[i].Content)
        if total+tokens > maxTokens {
            break
        }
        selected = append([]Message{messages[i]}, selected...)
        total += tokens
    }
    return selected, nil
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 会话不存在 | 404 | CONVERSATION_NOT_FOUND | 会话不存在 |
| 无权访问 | 403 | FORBIDDEN | 无权访问该会话 |
| 删除失败 | 500 | DELETE_FAILED | 删除会话失败 |
| 参数错误 | 400 | INVALID_REQUEST | 参数无效 |

---

## 8. Web 端适配要点

- 会话列表分页加载
- 删除会话二次确认
- 时间显示本地化
- 消息列表使用 `ListView.builder` 优化性能

---

## 9. 测试策略

- **单元测试**：上下文窗口截断、会话权限校验
- **集成测试**：会话 CRUD、消息分页、级联删除
- **接口测试**：401/403/404 场景

---

## 10. 检查清单

- [ ] 数据库 schema 与 migration
- [ ] Conversation 与 Message 模型
- [ ] Repository 与 Service 层
- [ ] REST API Handler
- [ ] 上下文窗口管理
- [ ] 权限校验
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
