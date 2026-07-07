# PRD：[S0-4] 设计数据库 Schema 并创建 migration

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](./AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-4 |
| **任务名称** | 设计数据库 Schema 并创建 migration |
| **所属史诗** | E0 基础设施 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S0-1 仓库初始化 |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要设计 MySQL 数据库 Schema，覆盖用户、资源、任务、会话和消息等核心实体，并通过 migration 工具管理 Schema 版本。该任务为后续用户认证、文件上传、任务追踪和对话系统提供数据持久化基础。

---

## 验收标准（AC）

- [ ] 根据 PRD 数据模型设计 MySQL Schema
- [ ] 创建 `users`、`resources`、`tasks`、`conversations`、`messages` 五张核心表
- [ ] 所有表包含 `id`、`created_at`、`updated_at`、`deleted_at` 标准字段（软删除）
- [ ] 主键统一使用 `BIGINT UNSIGNED AUTO_INCREMENT` 或 UUID
- [ ] 外键建立索引，字段使用合适的数据类型
- [ ] 使用 GORM migration 或 golang-migrate 创建初始 migration 文件
- [ ] migration 能在本地 MySQL 容器和 K8s MySQL 中成功运行
- [ ] 提供 `make migrate-up` 和 `make migrate-down` 命令
- [ ] Schema 文档写入 `docs/database-schema.md`

---

## 核心表设计

### 1. users（用户表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT UNSIGNED PK AI | 用户主键 |
| uuid | CHAR(36) UNIQUE NOT NULL | 对外暴露 UUID |
| email | VARCHAR(255) UNIQUE NOT NULL | 登录邮箱 |
| password_hash | VARCHAR(255) NOT NULL | bcrypt 哈希 |
| nickname | VARCHAR(100) | 昵称 |
| status | TINYINT DEFAULT 1 | 1=正常，2=禁用 |
| created_at | DATETIME(3) | 创建时间 |
| updated_at | DATETIME(3) | 更新时间 |
| deleted_at | DATETIME(3) NULL | 软删除 |

### 2. resources（资源表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT UNSIGNED PK AI | 主键 |
| uuid | CHAR(36) UNIQUE NOT NULL | 对外 UUID |
| user_id | BIGINT UNSIGNED NOT NULL FK | 所属用户 |
| name | VARCHAR(255) NOT NULL | 文件名 |
| type | VARCHAR(20) NOT NULL | `mp3` / `pdf` |
| status | TINYINT DEFAULT 1 | 1=上传中，2=处理中，3=完成，4=失败 |
| storage_key | VARCHAR(512) | MinIO 对象 key |
| size_bytes | BIGINT | 文件大小 |
| mime_type | VARCHAR(100) | MIME 类型 |
| metadata | JSON | 扩展元数据（页数、时长等） |
| created_at | DATETIME(3) | |
| updated_at | DATETIME(3) | |
| deleted_at | DATETIME(3) NULL | |

### 3. tasks（任务表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT UNSIGNED PK AI | 主键 |
| uuid | CHAR(36) UNIQUE NOT NULL | 对外 UUID |
| resource_id | BIGINT UNSIGNED NOT NULL FK | 关联资源 |
| user_id | BIGINT UNSIGNED NOT NULL FK | 所属用户 |
| type | VARCHAR(50) NOT NULL | `transcribe` / `parse` / `index` |
| status | VARCHAR(20) DEFAULT 'pending' | pending/processing/success/failed |
| progress | TINYINT UNSIGNED DEFAULT 0 | 进度 0-100 |
| result | JSON | 任务结果 |
| error_message | TEXT | 失败原因 |
| started_at | DATETIME(3) | 开始时间 |
| completed_at | DATETIME(3) | 完成时间 |
| created_at | DATETIME(3) | |
| updated_at | DATETIME(3) | |

### 4. conversations（会话表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT UNSIGNED PK AI | 主键 |
| uuid | CHAR(36) UNIQUE NOT NULL | 对外 UUID |
| user_id | BIGINT UNSIGNED NOT NULL FK | 所属用户 |
| title | VARCHAR(255) | 会话标题 |
| resource_ids | JSON | 关联资源 UUID 列表 |
| created_at | DATETIME(3) | |
| updated_at | DATETIME(3) | |
| deleted_at | DATETIME(3) NULL | |

### 5. messages（消息表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT UNSIGNED PK AI | 主键 |
| uuid | CHAR(36) UNIQUE NOT NULL | 对外 UUID |
| conversation_id | BIGINT UNSIGNED NOT NULL FK | 所属会话 |
| role | VARCHAR(20) NOT NULL | `user` / `assistant` / `system` |
| content | TEXT | 消息内容 |
| citations | JSON | 引用来源（时间戳/页码） |
| created_at | DATETIME(3) | |

---

## Migration 工具选择

- **方案 A（推荐）**：GORM AutoMigrate
  - 适合快速迭代，开发阶段友好
  - 自动同步模型到 Schema
- **方案 B（生产推荐）**：golang-migrate
  - SQL 版本化管理，适合团队协作
  - 推荐在 Sprint 2 后迁移到该方案

Sprint 0 先使用 GORM AutoMigrate 跑通，后续逐步引入 golang-migrate。

---

## 文件位置

```
gateway/
├── internal/
│   └── model/
│       ├── user.go
│       ├── resource.go
│       ├── task.go
│       ├── conversation.go
│       └── message.go
├── migrations/
│   └── 000001_init_schema.up.sql
│   └── 000001_init_schema.down.sql
└── Makefile
```

---

## 技术要点

- **字符集**：数据库默认 `utf8mb4`，支持 emoji 和中文
- **时间字段**：使用 `DATETIME(3)` 保留毫秒
- **软删除**：所有业务表保留 `deleted_at`，通过 GORM 软删除过滤
- **JSON 字段**：MySQL 5.7+ 支持 JSON，用于存储可变结构元数据
- **索引策略**：
  - `users.email` 唯一索引
  - `resources.user_id` 普通索引
  - `tasks.user_id` + `tasks.status` 组合索引
  - `messages.conversation_id` 普通索引

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 初期字段设计不全 | 后续频繁改表 | 预留 JSON 扩展字段，核心字段覆盖 80% 场景 |
| GORM 和 migration 工具混用 | 版本混乱 | 先用 GORM AutoMigrate，稳定后切 golang-migrate |

---

## 备注

- 本任务只创建 Schema 和 migration，不实现业务接口
- 字段命名采用蛇形命名，与 GORM 默认 tag 对齐
- 向量数据（Embedding）存 Milvus，不存 MySQL
