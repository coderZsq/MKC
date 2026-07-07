# 技术文档：[S0-4] 数据库 Schema 设计与 Migration 策略

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 级别：架构师/后端负责人  
> 关联 PRD：[PRD_S0-4_database_schema_migration.md](../prd/PRD_S0-4_database_schema_migration.md)

---

## 1. 文档目标

本文档定义 MKC 项目 MySQL 数据库的完整 Schema 设计、索引策略、软删除机制、Migration 工具选型、版本管理策略以及向生产环境扩展的预留方案。

---

## 2. 设计原则

| 原则 | 说明 |
|---|---|
| 单一事实来源 | MySQL 仅存储业务元数据，大文件/向量存外部存储 |
| 软删除优先 | 所有业务表保留 `deleted_at`，便于数据恢复和审计 |
| UUID 对外 | 对外暴露 `uuid` 字段，内部主键使用自增 ID |
| JSON 扩展 | 使用 JSON 字段存储可变结构元数据，避免频繁 DDL |
| 索引保守 | 先建必要索引，后续根据慢查询逐步增加 |
| 字符集统一 | 默认 `utf8mb4`，支持 emoji 和多语言 |

---

## 3. ER 关系图

```
users ||--o{ resources : owns
users ||--o{ conversations : owns
users ||--o{ tasks : owns
resources ||--o{ tasks : has
conversations ||--o{ messages : contains
```

---

## 4. 表结构设计

### 4.1 users（用户表）

```sql
CREATE TABLE users (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid            CHAR(36) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    nickname        VARCHAR(100) DEFAULT NULL,
    avatar_url      VARCHAR(512) DEFAULT NULL,
    status          TINYINT UNSIGNED DEFAULT 1 COMMENT '1=active, 2=disabled',
    created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    deleted_at      DATETIME(3) DEFAULT NULL,
    INDEX idx_users_created_at (created_at),
    INDEX idx_users_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**设计说明**：
- `id` 用于内部关联和索引，`uuid` 用于 API 暴露
- `email` 唯一索引用于登录
- `password_hash` 使用 bcrypt 生成，长度固定 60

### 4.2 resources（资源表）

```sql
CREATE TABLE resources (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid            CHAR(36) NOT NULL UNIQUE,
    user_id         BIGINT UNSIGNED NOT NULL,
    name            VARCHAR(255) NOT NULL,
    type            VARCHAR(20) NOT NULL COMMENT 'mp3, pdf',
    status          TINYINT UNSIGNED DEFAULT 1 COMMENT '1=uploading, 2=processing, 3=completed, 4=failed',
    storage_key     VARCHAR(512) DEFAULT NULL COMMENT 'MinIO object key',
    size_bytes      BIGINT DEFAULT 0,
    mime_type       VARCHAR(100) DEFAULT NULL,
    duration_seconds INT DEFAULT NULL COMMENT '音频时长',
    page_count      INT DEFAULT NULL COMMENT 'PDF 页数',
    metadata        JSON DEFAULT NULL,
    created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    deleted_at      DATETIME(3) DEFAULT NULL,
    INDEX idx_resources_user_id (user_id),
    INDEX idx_resources_user_status (user_id, status),
    INDEX idx_resources_type (type),
    INDEX idx_resources_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**设计说明**：
- `metadata` 存储扩展信息，如采样率、编码格式、目录结构等
- `status` 用于驱动资源卡片展示
- `storage_key` 不存完整 URL，避免域名变更影响数据

### 4.3 tasks（任务表）

```sql
CREATE TABLE tasks (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid            CHAR(36) NOT NULL UNIQUE,
    resource_id     BIGINT UNSIGNED NOT NULL,
    user_id         BIGINT UNSIGNED NOT NULL,
    type            VARCHAR(50) NOT NULL COMMENT 'transcribe, parse, index, summarize',
    status          VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending, processing, success, failed, cancelled',
    progress        TINYINT UNSIGNED DEFAULT 0 COMMENT '0-100',
    result          JSON DEFAULT NULL,
    error_message   TEXT DEFAULT NULL,
    started_at      DATETIME(3) DEFAULT NULL,
    completed_at    DATETIME(3) DEFAULT NULL,
    retry_count     TINYINT UNSIGNED DEFAULT 0,
    created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    INDEX idx_tasks_user_id (user_id),
    INDEX idx_tasks_resource_id (resource_id),
    INDEX idx_tasks_user_status (user_id, status),
    INDEX idx_tasks_status_created (status, created_at),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**设计说明**：
- `result` 存储任务输出摘要，如 SRT 文件 key、文本摘要、向量集合名等
- `retry_count` 配合 Celery 重试策略使用
- `status` 使用字符串枚举，便于调试和日志识别

### 4.4 conversations（会话表）

```sql
CREATE TABLE conversations (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid            CHAR(36) NOT NULL UNIQUE,
    user_id         BIGINT UNSIGNED NOT NULL,
    title           VARCHAR(255) DEFAULT NULL,
    resource_ids    JSON DEFAULT NULL COMMENT '关联资源 UUID 列表',
    model_config    JSON DEFAULT NULL COMMENT '模型参数、温度等',
    created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    deleted_at      DATETIME(3) DEFAULT NULL,
    INDEX idx_conversations_user_id (user_id),
    INDEX idx_conversations_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4.5 messages（消息表）

```sql
CREATE TABLE messages (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid                CHAR(36) NOT NULL UNIQUE,
    conversation_id     BIGINT UNSIGNED NOT NULL,
    parent_message_id   BIGINT UNSIGNED DEFAULT NULL COMMENT '支持分支对话',
    role                VARCHAR(20) NOT NULL COMMENT 'user, assistant, system',
    content             TEXT NOT NULL,
    citations           JSON DEFAULT NULL COMMENT '引用来源 [{resource_uuid, type, timestamp/page}]',
    token_usage         JSON DEFAULT NULL COMMENT '{prompt_tokens, completion_tokens}',
    created_at          DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_messages_conversation_id (conversation_id),
    INDEX idx_messages_conversation_created (conversation_id, created_at),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**设计说明**：
- `citations` 支持音频时间戳和 PDF 页码引用
- `parent_message_id` 为未来分支对话预留
- 消息表不软删除，会话删除级联删除消息

### 4.6 sessions（Redis 替代）

Session 信息存储在 Redis 而非 MySQL，包括：
- refresh_token → user_id 映射
- 多设备会话列表
- 登录失败计数

---

## 5. 索引设计总览

| 表 | 索引名 | 字段 | 用途 |
|---|---|---|---|
| users | PRIMARY | id | 内部关联 |
| users | uk_uuid | uuid | API 暴露 |
| users | uk_email | email | 登录唯一性 |
| resources | idx_user_status | user_id, status | 任务中心筛选 |
| tasks | idx_user_status | user_id, status | 任务列表查询 |
| tasks | idx_status_created | status, created_at | 后台任务扫描 |
| messages | idx_conversation_created | conversation_id, created_at | 历史消息分页 |

---

## 6. Migration 策略

### 6.1 工具选型对比

| 工具 | 优点 | 缺点 | 适用阶段 |
|---|---|---|---|
| GORM AutoMigrate | 快速迭代，自动生成 | 不适合团队协作，变更不可控 | Sprint 0-1 |
| golang-migrate | SQL 版本化，可控 | 需要手写 SQL | Sprint 2+ |
| Atlas | 可视化 Schema 管理 | 学习成本 | 生产环境 |

### 6.2 Sprint 0 方案

使用 **GORM AutoMigrate** 快速跑通：

```go
package repository

import (
    "gorm.io/gorm"
    "github.com/coderZsq/mkc/gateway/internal/model"
)

func AutoMigrate(db *gorm.DB) error {
    return db.AutoMigrate(
        &model.User{},
        &model.Resource{},
        &model.Task{},
        &model.Conversation{},
        &model.Message{},
    )
}
```

### 6.3 GORM 模型定义

```go
package model

import (
    "time"
    "gorm.io/gorm"
)

type User struct {
    ID           uint64    `gorm:"primaryKey;autoIncrement"`
    UUID         string    `gorm:"type:char(36);uniqueIndex;not null"`
    Email        string    `gorm:"type:varchar(255);uniqueIndex;not null"`
    PasswordHash string    `gorm:"type:varchar(255);not null"`
    Nickname     string    `gorm:"type:varchar(100)"`
    Status       uint8     `gorm:"default:1"`
    CreatedAt    time.Time `gorm:"type:datetime(3)"`
    UpdatedAt    time.Time `gorm:"type:datetime(3)"`
    DeletedAt    gorm.DeletedAt `gorm:"index"`
}
```

### 6.4 迁移到 golang-migrate

Sprint 2 后引入：

```
gateway/migrations/
├── 000001_init_schema.up.sql
├── 000001_init_schema.down.sql
├── 000002_add_task_retry_count.up.sql
└── 000002_add_task_retry_count.down.sql
```

```yaml
# docker-compose 本地迁移示例
migrate:
  image: migrate/migrate
  volumes:
    - ./gateway/migrations:/migrations
  command: ["-path", "/migrations", "-database", "mysql://user:pass@tcp(mysql:3306)/mkc", "up"]
```

---

## 7. 连接池配置

```yaml
database:
  host: mysql
  port: 3306
  user: mkc
  password: ""
  dbname: mkc
  charset: utf8mb4
  parse_time: true
  loc: Local
  max_open_conns: 25
  max_idle_conns: 5
  conn_max_lifetime: 30m
```

```go
sqlDB, err := db.DB()
sqlDB.SetMaxOpenConns(cfg.MaxOpenConns)
sqlDB.SetMaxIdleConns(cfg.MaxIdleConns)
sqlDB.SetConnMaxLifetime(cfg.ConnMaxLifetime)
```

---

## 8. 扩展性预留

| 场景 | 预留方案 |
|---|---|
| 用户量增长 | 按 user_id 分库分表（ShardingSphere / Vitess） |
| 消息表膨胀 | 按时间归档，历史消息存对象存储 |
| 多租户 | 增加 `tenant_id` 字段，所有查询带上过滤 |
| 读写分离 | GORM 配置多个 DSN，读走从库 |
| 审计 | 增加 `created_by`/`updated_by` 字段或审计日志表 |

---

## 9. 检查清单

- [ ] 五张核心表创建完成
- [ ] 所有表使用 utf8mb4 字符集
- [ ] UUID 唯一索引建立
- [ ] 外键和级联删除配置正确
- [ ] GORM 模型与 Schema 一致
- [ ] AutoMigrate 在本地 K8s MySQL 成功运行
- [ ] 连接池参数调优
- [ ] Schema 文档同步更新
