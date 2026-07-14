CREATE INDEX idx_tasks_resource_status_completed
    ON tasks (resource_id, status, completed_at);
