# PRD：[S3-8] 会话与消息持久化

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S0-4_database_schema_migration.md](./PRD_S0-4_database_schema_migration.md)、[PRD_S1-7_task_progress_push.md](./PRD_S1-7_task_progress_push.md)、[PRD_S3-6_sse_qa_api.md](./PRD_S3-6_sse_qa_api.md)、[PRD_S3-7_flutter_chat_page.md](./PRD_S3-7_flutter_chat_page.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-8 |
| **任务名称** | 会话与消息持久化 |
| **所属史诗** | E7 AI 对话 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S0-4 数据库 Schema |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为用户，我希望与知识库助手的多轮对话历史被持久化，以便在不同时间、不同设备上继续会话。本任务在 Gateway 设计并实现会话（conversation）与消息（message）的数据模型、数据库表、REST API 与上下文窗口管理。该服务为 S3-6 问答 API 提供历史消息，为 S3-7 对话页面提供历史列表与详情。

---

## 验收标准（AC）

- [ ] **AC-1** 数据库新增 `conversations` 与 `messages` 表，支持会话与消息 CRUD
- [ ] **AC-2** Gateway 提供 `POST /api/v1/conversations` 创建会话，`GET /api/v1/conversations` 列出会话
- [ ] **AC-3** Gateway 提供 `GET /api/v1/conversations/{id}/messages` 分页获取消息历史
- [ ] **AC-4** 用户只能访问自己创建的会话，越权访问返回 403
- [ ] **AC-5** 消息角色支持 `user` 与 `assistant`，并记录创建时间、token 用量、模型名等元数据
- [ ] **AC-6** 上下文窗口管理：构造 LLM 请求时按 token 预算截断历史消息，保留最新对话
- [ ] **AC-7** 删除会话时级联删除其消息
- [ ] **AC-8** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
gateway/
├── internal/
│   ├── model/
│   │   ├── conversation.go
│   │   └── message.go
│   ├── repository/
│   │   ├── conversation_repository.go
│   │   └── message_repository.go
│   ├── service/
│   │   ├── conversation_service.go
│   │   └── context_window_service.go
│   ├── handler/
│   │   ├── conversation_handler.go
│   │   └── message_handler.go
│   └── migration/
│       └── 003_conversations_messages.up.sql
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| GORM | 1.25.x | ORM 与 migration |
| MySQL | 8.0+ | 持久化存储 |
| tiktoken | 0.7.x | 上下文 token 估算（AI Service 中复用） |

---

## 技术要点

### 数据库 Schema

```sql
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(255),
    resource_ids JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
);

CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    citations JSON,
    model VARCHAR(64),
    token_usage INT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
```

### 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/conversations` | Bearer JWT | 创建会话 |
| GET | `/api/v1/conversations` | Bearer JWT | 列出会话，分页 |
| GET | `/api/v1/conversations/{id}` | Bearer JWT | 会话详情 |
| DELETE | `/api/v1/conversations/{id}` | Bearer JWT | 删除会话 |
| GET | `/api/v1/conversations/{id}/messages` | Bearer JWT | 消息历史，分页 |
| POST | `/api/v1/conversations/{id}/messages` | Bearer JWT | 创建用户消息（S3-6 内部使用） |

### 上下文窗口管理

- 默认保留最近 10 轮对话（20 条消息）
- 按 token 估算动态截断，确保当前问题 + 上下文不超过 LLM 最大上下文
- 优先保留最新的用户问题与最近回答

### 错误处理

- 会话不存在或无权访问：404/403
- 删除失败：500 并记录日志
- 消息越权：校验 conversation 归属 user

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 上下文窗口截断逻辑复杂 | LLM 输入超出限制 | 使用 token 估算，逐步截断 |
| 会话列表查询慢 | 用户量大时卡顿 | 按 user_id 索引，分页返回 |
| 消息与流式生成并发写入 | 数据不一致 | Gateway 统一落库，使用事务 |

---

## Web 端适配

- 会话与消息 API 为 REST 接口，Web 端通过 dio 调用
- 会话列表支持下拉刷新与分页加载
- 删除会话时二次确认
- Web 端时间显示使用 `intl` 本地化

---

## 备注

- 会话标题可由第一条用户问题自动生成（前 20 字）
- 资源范围（resource_ids）存储在 conversation 中，便于后续问答复用
- 删除会话需要级联删除消息，避免脏数据
- 为 S4 Agent 工作流预留 `metadata` JSON 字段，可存储意图、标签等扩展信息
