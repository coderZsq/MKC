# S0-4 测试用例：数据库 Schema 与 Migration

## 1. 范围与目标

验证 MySQL Schema 设计符合 PRD 数据模型，五张核心表结构、索引、软删除、JSON 字段、字符集、时间精度正确；migration 工具在本地容器与 K8s MySQL 中均可幂等执行。

## 2. 测试环境

- 本地 MySQL 8.0 容器或 K8s MySQL 已 Ready
- 已配置数据库连接信息
- 可选：GORM AutoMigrate 与 golang-migrate CLI 均可使用

## 3. 测试用例

### 3.1 表结构与存在性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-001 | Functional | Integration | P0 | 五张核心表存在 | migration 已执行 | `SHOW TABLES;` | 存在 `users`、`resources`、`tasks`、`conversations`、`messages` | PRD AC-2 |
| MKC-TC-S0-4-002 | Functional | Integration | P0 | `users` 表字段符合设计 | 表存在 | `DESCRIBE users;` | 包含 id、uuid、email、password_hash、nickname、status、created_at、updated_at、deleted_at | PRD users |
| MKC-TC-S0-4-003 | Functional | Integration | P0 | `resources` 表字段符合设计 | 表存在 | `DESCRIBE resources;` | 包含 id、uuid、user_id、name、type、status、storage_key、size_bytes、mime_type、metadata、created_at、updated_at、deleted_at | PRD resources |
| MKC-TC-S0-4-004 | Functional | Integration | P0 | `tasks` 表字段符合设计 | 表存在 | `DESCRIBE tasks;` | 包含 id、uuid、resource_id、user_id、type、status、progress、result、error_message、started_at、completed_at、created_at、updated_at | PRD tasks |
| MKC-TC-S0-4-005 | Functional | Integration | P0 | `conversations` 表字段符合设计 | 表存在 | `DESCRIBE conversations;` | 包含 id、uuid、user_id、title、resource_ids、created_at、updated_at、deleted_at | PRD conversations |
| MKC-TC-S0-4-006 | Functional | Integration | P0 | `messages` 表字段符合设计 | 表存在 | `DESCRIBE messages;` | 包含 id、uuid、conversation_id、role、content、citations、created_at | PRD messages |

### 3.2 主键、唯一键与外键

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-007 | Functional | Integration | P0 | 所有表主键为 `BIGINT UNSIGNED AUTO_INCREMENT` | 表存在 | `SHOW CREATE TABLE users;` 等 | 主键定义为 `BIGINT UNSIGNED AUTO_INCREMENT` | PRD AC-3 |
| MKC-TC-S0-4-008 | Functional | Integration | P0 | 业务表 `uuid` 字段唯一且非空 | 表存在 | `SHOW CREATE TABLE users;` | `uuid CHAR(36) UNIQUE NOT NULL` | PRD 表设计 |
| MKC-TC-S0-4-009 | Functional | Integration | P1 | `users.email` 唯一索引 | 表存在 | `SHOW INDEX FROM users;` | 存在 `email` 唯一索引 | PRD 索引策略 |
| MKC-TC-S0-4-010 | Functional | Integration | P1 | `resources.user_id` 外键/索引 | 表存在 | `SHOW CREATE TABLE resources;` | `user_id` 有索引；如有外键则 ON DELETE/UPDATE 策略明确 | PRD 索引策略 |
| MKC-TC-S0-4-011 | Functional | Integration | P1 | `tasks` 组合索引 `(user_id, status)` | 表存在 | `SHOW INDEX FROM tasks;` | 存在 `user_id` + `status` 组合索引 | PRD 索引策略 |
| MKC-TC-S0-4-012 | Functional | Integration | P1 | `messages.conversation_id` 索引 | 表存在 | `SHOW INDEX FROM messages;` | 存在 `conversation_id` 索引 | PRD 索引策略 |
| MKC-TC-S0-4-013 | Negative | Integration | P1 | 插入重复 email 失败 | users 表已创建 | 插入两条 email 相同的记录 | 第二条插入因唯一约束失败 | PRD 索引策略 |
| MKC-TC-S0-4-014 | Negative | Integration | P1 | 插入重复 uuid 失败 | users 表已创建 | 插入两条 uuid 相同的记录 | 第二条插入因唯一约束失败 | PRD 表设计 |

### 3.3 数据类型与边界

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-015 | Functional | Integration | P0 | 时间字段为 `DATETIME(3)` | 表存在 | `SHOW CREATE TABLE users;` | `created_at`、`updated_at`、`deleted_at` 为 `DATETIME(3)` | PRD 技术要点 |
| MKC-TC-S0-4-016 | Functional | Integration | P1 | `users.status` 默认值为 1 | 表存在 | `SHOW CREATE TABLE users;` | `status` 默认 `1` | PRD users |
| MKC-TC-S0-4-017 | Functional | Integration | P1 | `resources.status` 默认值为 1 | 表存在 | `SHOW CREATE TABLE resources;` | `status` 默认 `1` | PRD resources |
| MKC-TC-S0-4-018 | Functional | Integration | P1 | `tasks.status` 默认值为 `pending` | 表存在 | `SHOW CREATE TABLE tasks;` | `status` 默认 `'pending'` | PRD tasks |
| MKC-TC-S0-4-019 | Functional | Integration | P1 | `tasks.progress` 默认值为 0 | 表存在 | `SHOW CREATE TABLE tasks;` | `progress` 默认 `0` | PRD tasks |
| MKC-TC-S0-4-020 | Boundary | Integration | P1 | `users.email` 最大长度 255 | 表存在 | 插入 255 字符邮箱与 256 字符邮箱 | 255 成功，256 失败 | PRD users |
| MKC-TC-S0-4-021 | Boundary | Integration | P2 | `users.nickname` 最大长度 100 | 表存在 | 插入 100 与 101 字符昵称 | 100 成功，101 失败 | PRD users |
| MKC-TC-S0-4-022 | Boundary | Integration | P2 | `resources.storage_key` 最大长度 512 | 表存在 | 插入 512 与 513 字符 key | 512 成功，513 失败 | PRD resources |
| MKC-TC-S0-4-023 | Boundary | Integration | P2 | `tasks.progress` 有效范围 0-100 | 表存在 | 插入 0、100、101 | 0 与 100 成功，101 失败（应用层或 DB 层约束） | PRD tasks |

### 3.4 软删除

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-024 | Functional | Integration | P0 | 业务表包含 `deleted_at` 字段 | 表存在 | `DESCRIBE` users/resources/conversations | 均存在 `deleted_at DATETIME(3) NULL` | PRD AC-3 |
| MKC-TC-S0-4-025 | Functional | Integration | P1 | GORM 软删除标记不物理删除 | 已通过 GORM 创建记录 | 调用 `Delete(&user)` | `deleted_at` 被设置为当前时间，记录仍存在于表中 | PRD 技术要点 |
| MKC-TC-S0-4-026 | Functional | Integration | P1 | 普通查询自动过滤软删除记录 | 存在软删除记录 | `db.Find(&users)` | 结果集中不包含 `deleted_at IS NOT NULL` 的记录 | PRD 技术要点 |
| MKC-TC-S0-4-027 | Functional | Integration | P2 | `Unscoped` 查询可读取已删除记录 | 存在软删除记录 | `db.Unscoped().Find(&users)` | 包含已删除记录 | GORM 行为 |

### 3.5 JSON 字段与字符集

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-028 | Functional | Integration | P0 | JSON 字段可写入有效对象 | resources / conversations / tasks 表存在 | 插入包含 `metadata`、`resource_ids`、`result` 等 JSON 的记录 | 写入成功，读取后 JSON 结构完整 | PRD 技术要点 |
| MKC-TC-S0-4-029 | Negative | Integration | P1 | JSON 字段写入非法格式失败 | 表存在 | 插入非 JSON 字符串到 metadata | MySQL 报错 `Invalid JSON text` | PRD 技术要点 |
| MKC-TC-S0-4-030 | Functional | Integration | P0 | 数据库与表字符集为 `utf8mb4` | 数据库存在 | `SHOW CREATE DATABASE mkc;` 与 `SHOW CREATE TABLE users;` | 字符集为 `utf8mb4_0900_ai_ci` 或等效 utf8mb4 | PRD 技术要点 |
| MKC-TC-S0-4-031 | Boundary | Integration | P1 | 可存储中文与 emoji | 表存在 | 插入 nickname = "测试🚀" 与 content = "你好🌍" | 读取结果完全一致，无乱码 | PRD 技术要点 |

### 3.6 Migration 工具

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-032 | Functional | Integration | P0 | `migrations/000001_init_schema.up.sql` 存在 | 仓库已克隆 | `ls gateway/migrations/` | 存在 up / down migration 文件 | PRD AC-6 |
| MKC-TC-S0-4-033 | Functional | Integration | P0 | Migration 在本地 MySQL 容器成功执行 | Docker MySQL 运行 | `make migrate-up` 或 `golang-migrate -path ... up` | 五张表成功创建 | PRD AC-7 |
| MKC-TC-S0-4-034 | Functional | Integration | P0 | Migration 在 K8s MySQL 成功执行 | K8s MySQL Ready | 端口转发后执行 `make migrate-up` | 五张表成功创建 | PRD AC-7 |
| MKC-TC-S0-4-035 | Functional | Integration | P1 | `make migrate-down` 可回滚 | migration 已 up | `make migrate-down` | 五张表被删除或回退到迁移前状态 | PRD AC-7 |
| MKC-TC-S0-4-036 | Idempotency | Integration | P0 | 重复执行 up migration 不报错 | 已执行过一次 up | 再次执行 `make migrate-up` | 命令成功，Schema 无重复对象 | PRD AC-6 |
| MKC-TC-S0-4-037 | Idempotency | Integration | P1 | up 后 down 再 up 状态一致 | 数据库干净 | 1. up；2. down；3. up；4. 对比 Schema | 最终 Schema 与首次 up 一致 | PRD AC-6 |
| MKC-TC-S0-4-038 | Functional | Integration | P1 | GORM AutoMigrate 可同步模型到 Schema | Gateway 模型已编写 | 运行 `db.AutoMigrate(&models...)` | 五张表存在且结构与 migration 一致 | PRD AC-5 |
| MKC-TC-S0-4-039 | Concurrency | Integration | P2 | 多实例同时启动不会重复建表 | 多副本 Gateway | 同时启动两个 Pod | 只有一个成功执行 DDL 或均幂等成功，无报错 | 工程最佳实践 |

### 3.7 GORM 模型

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-040 | Functional | Unit | P1 | GORM 模型文件存在于 `gateway/internal/model/` | 仓库已克隆 | `ls gateway/internal/model/` | 存在 user.go、resource.go、task.go、conversation.go、message.go | PRD 文件位置 |
| MKC-TC-S0-4-041 | Functional | Unit | P1 | 模型字段与数据库列一一对应 | 模型文件存在 | 读取模型结构体标签 | `gorm:"column:xxx"` 或默认蛇形命名与 Schema 一致 | PRD 技术要点 |
| MKC-TC-S0-4-042 | Functional | Unit | P2 | 模型嵌入基础字段（ID、时间、软删） | 模型文件存在 | 检查是否嵌入 `gorm.Model` 或自定义 BaseModel | 包含 ID、CreatedAt、UpdatedAt、DeletedAt | PRD 文件位置 |

### 3.8 索引性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-043 | Performance | Integration | P2 | `tasks(user_id, status)` 索引被查询使用 | 表中有 1 万条记录 | `EXPLAIN SELECT * FROM tasks WHERE user_id = ? AND status = ?` | type 为 `ref` 或 `range`，key 为组合索引 | PRD 索引策略 |
| MKC-TC-S0-4-044 | Performance | Integration | P2 | `messages(conversation_id)` 索引被查询使用 | 表中有 1 万条记录 | `EXPLAIN SELECT * FROM messages WHERE conversation_id = ?` | type 为 `ref`，key 为 conversation_id 索引 | PRD 索引策略 |
| MKC-TC-S0-4-045 | Performance | Integration | P2 | `users.email` 唯一索引保证点查效率 | 表中有 1 万条记录 | `EXPLAIN SELECT * FROM users WHERE email = ?` | type 为 `const` 或 `eq_ref` | PRD 索引策略 |

### 3.9 异常与安全性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-4-046 | Exception | Integration | P1 | 连接失败时 migration 给出明确错误 | 数据库未启动 | `make migrate-up` | 命令返回非零退出码并提示连接失败 | 工程最佳实践 |
| MKC-TC-S0-4-047 | Exception | Integration | P1 | down migration 在表不存在时行为可控 | 已手动删除表 | `make migrate-down` | 命令成功或给出清晰警告，不破坏其他对象 | PRD AC-7 |
| MKC-TC-S0-4-048 | Security | Integration | P0 | migration 使用的数据库用户非 root | 已配置用户 | 查看 `make migrate-up` 使用的 DSN | 使用 `mkc` 等业务用户，而非 root | 安全基线 |
| MKC-TC-S0-4-049 | Security | Static | P1 | migration 文件无真实密码 | 仓库已克隆 | `grep -i "password" gateway/migrations/*.sql` | 无具体密码值 | 安全基线 |

## 4. 测试执行清单

- [ ] 五张核心表结构与 PRD 完全一致
- [ ] 索引与外键约束符合索引策略
- [ ] `DATETIME(3)` 与 `utf8mb4` 已验证
- [ ] 软删除逻辑正确
- [ ] `make migrate-up` / `make migrate-down` 在本地与 K8s 均通过
- [ ] 重复执行 migration 幂等
- [ ] 无硬编码数据库密码

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
