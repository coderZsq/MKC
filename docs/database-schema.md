# Database Schema

The gateway service uses **MySQL 8** with **utf8mb4** and **InnoDB**. Date/time columns use `DATETIME(3)` for millisecond precision. Soft delete is implemented with `deleted_at` and GORM `gorm.DeletedAt`.

## Tables

| Table | Purpose | Soft Delete |
|---|---|---|
| `users` | Registered accounts | Yes |
| `resources` | Uploaded multimedia files | Yes |
| `tasks` | Asynchronous processing jobs | No |
| `conversations` | Chat sessions owned by a user | Yes |
| `messages` | Conversation messages / turns | No |

## Entity Relationships

- A `user` owns many `resources`, `tasks`, and `conversations`.
- A `resource` is referenced by many `tasks`.
- A `conversation` contains many `messages`.
- A `message` may reference a parent `message` (self-referential).

## Key Indexes

- All `uuid` columns have a unique index (`uk_<table>_uuid`).
- Foreign keys are indexed and enforced with `ON DELETE CASCADE`, except `messages.parent_message_id` which uses `ON DELETE SET NULL`.
- Composite indexes support common query patterns:
  - `idx_resources_user_status (user_id, status)`
  - `idx_tasks_user_status (user_id, status)`
  - `idx_tasks_status_created (status, created_at)`
  - `idx_messages_conversation_created (conversation_id, created_at)`

## Migration

Run migrations using the Makefile:

```bash
cd gateway
export MYSQL_DSN="user:password@tcp(127.0.0.1:3306)/mkc?charset=utf8mb4&parseTime=True&loc=Local"
make migrate-up
make migrate-down
```

Migrations are also available as raw SQL in `gateway/migrations/`.
