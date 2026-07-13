CREATE TABLE IF NOT EXISTS summaries (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    resource_id BIGINT UNSIGNED NOT NULL,
    type        VARCHAR(20)     NOT NULL,
    content     TEXT            NOT NULL,
    section_meta JSON,
    model       VARCHAR(100),
    tokens      INT             DEFAULT 0,
    fallback    BOOLEAN         DEFAULT FALSE,
    created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

    KEY idx_summaries_resource_type (resource_id, type),

    CONSTRAINT fk_summaries_resource_id
        FOREIGN KEY (resource_id) REFERENCES resources(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
