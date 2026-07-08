package model

import (
	"encoding/json"
	"time"
)

// Task represents an asynchronous processing job for a resource.
type Task struct {
	ID           uint64          `gorm:"column:id;primaryKey;autoIncrement"`
	UUID         string          `gorm:"column:uuid;type:char(36);uniqueIndex:uk_tasks_uuid;not null"`
	ResourceID   uint64          `gorm:"column:resource_id;type:bigint unsigned;not null;index:idx_tasks_resource_id"`
	UserID       uint64          `gorm:"column:user_id;type:bigint unsigned;not null;index:idx_tasks_user_id;index:idx_tasks_user_status"`
	Type         string          `gorm:"column:type;type:varchar(50);not null"`
	Status       string          `gorm:"column:status;type:varchar(20);default:pending;index:idx_tasks_user_status;index:idx_tasks_status_created"`
	Progress     uint8           `gorm:"column:progress;type:tinyint unsigned;default:0"`
	Result       json.RawMessage `gorm:"column:result;type:json"`
	ErrorMessage string          `gorm:"column:error_message;type:text"`
	StartedAt    *time.Time      `gorm:"column:started_at;type:datetime"`
	CompletedAt  *time.Time      `gorm:"column:completed_at;type:datetime"`
	RetryCount   uint8           `gorm:"column:retry_count;type:tinyint unsigned;default:0"`
	CreatedAt    time.Time       `gorm:"column:created_at;type:datetime;autoCreateTime"`
	UpdatedAt    time.Time       `gorm:"column:updated_at;type:datetime;autoUpdateTime"`

	Resource Resource `gorm:"foreignKey:ResourceID;references:ID;constraint:OnDelete:CASCADE"`
	User     User     `gorm:"foreignKey:UserID;references:ID;constraint:OnDelete:CASCADE"`
}

// Task status constants.
const (
	TaskStatusPending   = "pending"
	TaskStatusRunning   = "running"
	TaskStatusCompleted = "completed"
	TaskStatusFailed    = "failed"
)
