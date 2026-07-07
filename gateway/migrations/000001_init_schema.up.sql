CREATE TABLE IF NOT EXISTS users (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid            CHAR(36)        NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    nickname        VARCHAR(100),
    avatar_url      VARCHAR(512),
    status          TINYINT UNSIGNED DEFAULT 1,
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    deleted_at      DATETIME(3)     NULL,

    UNIQUE KEY uk_users_uuid  (uuid),
    UNIQUE KEY uk_users_email (email),
    KEY idx_users_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS resources (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid             CHAR(36)        NOT NULL,
    user_id          BIGINT UNSIGNED NOT NULL,
    name             VARCHAR(255)    NOT NULL,
    type             VARCHAR(20)     NOT NULL,
    status           TINYINT UNSIGNED DEFAULT 1,
    storage_key      VARCHAR(512),
    size_bytes       BIGINT          DEFAULT 0,
    mime_type        VARCHAR(100),
    duration_seconds INT,
    page_count       INT,
    metadata         JSON,
    created_at       DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at       DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    deleted_at       DATETIME(3)     NULL,

    UNIQUE KEY uk_resources_uuid (uuid),
    KEY idx_resources_user_id      (user_id),
    KEY idx_resources_type         (type),
    KEY idx_resources_user_status  (user_id, status),
    KEY idx_resources_deleted_at   (deleted_at),

    CONSTRAINT fk_resources_user_id
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tasks (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid           CHAR(36)        NOT NULL,
    resource_id    BIGINT UNSIGNED NOT NULL,
    user_id        BIGINT UNSIGNED NOT NULL,
    type           VARCHAR(50)     NOT NULL,
    status         VARCHAR(20)     NOT NULL DEFAULT 'pending',
    progress       TINYINT UNSIGNED DEFAULT 0,
    result         JSON,
    error_message  TEXT,
    started_at     DATETIME(3)     NULL,
    completed_at   DATETIME(3)     NULL,
    retry_count    TINYINT UNSIGNED DEFAULT 0,
    created_at     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

    UNIQUE KEY uk_tasks_uuid (uuid),
    KEY idx_tasks_resource_id      (resource_id),
    KEY idx_tasks_user_id          (user_id),
    KEY idx_tasks_user_status      (user_id, status),
    KEY idx_tasks_status_created   (status, created_at),

    CONSTRAINT fk_tasks_resource_id
        FOREIGN KEY (resource_id) REFERENCES resources(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_tasks_user_id
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS conversations (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid         CHAR(36)        NOT NULL,
    user_id      BIGINT UNSIGNED NOT NULL,
    title        VARCHAR(255),
    resource_ids JSON,
    model_config JSON,
    created_at   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    deleted_at   DATETIME(3)     NULL,

    UNIQUE KEY uk_conversations_uuid (uuid),
    KEY idx_conversations_user_id    (user_id),
    KEY idx_conversations_deleted_at (deleted_at),

    CONSTRAINT fk_conversations_user_id
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
    id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid              CHAR(36)        NOT NULL,
    conversation_id   BIGINT UNSIGNED NOT NULL,
    parent_message_id BIGINT UNSIGNED NULL,
    role              VARCHAR(20)     NOT NULL,
    content           TEXT            NOT NULL,
    citations         JSON,
    token_usage       JSON,
    created_at        DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE KEY uk_messages_uuid (uuid),
    KEY idx_messages_conversation_id           (conversation_id),
    KEY idx_messages_conversation_created      (conversation_id, created_at),
    KEY idx_messages_parent_message_id         (parent_message_id),

    CONSTRAINT fk_messages_conversation_id
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_messages_parent_message_id
        FOREIGN KEY (parent_message_id) REFERENCES messages(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
