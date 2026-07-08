package model

import (
	"encoding/json"
	"time"

	"gorm.io/gorm"
)

// Resource represents an uploaded multimedia file.
type Resource struct {
	ID              uint64          `gorm:"column:id;primaryKey;autoIncrement"`
	UUID            string          `gorm:"column:uuid;type:char(36);uniqueIndex:uk_resources_uuid;not null"`
	UserID          uint64          `gorm:"column:user_id;type:bigint unsigned;not null;index:idx_resources_user_id;index:idx_resources_user_status"`
	Name            string          `gorm:"column:name;type:varchar(255);not null"`
	Type            string          `gorm:"column:type;type:varchar(20);not null;index:idx_resources_type"`
	Status          uint8           `gorm:"column:status;type:tinyint unsigned;default:1;index:idx_resources_user_status"`
	StorageKey      string          `gorm:"column:storage_key;type:varchar(512)"`
	SizeBytes       int64           `gorm:"column:size_bytes;type:bigint;default:0"`
	MimeType        string          `gorm:"column:mime_type;type:varchar(100)"`
	DurationSeconds *int            `gorm:"column:duration_seconds;type:int"`
	PageCount       *int            `gorm:"column:page_count;type:int"`
	Metadata        json.RawMessage `gorm:"column:metadata;type:json"`
	CreatedAt       time.Time       `gorm:"column:created_at;type:datetime;autoCreateTime"`
	UpdatedAt       time.Time       `gorm:"column:updated_at;type:datetime;autoUpdateTime"`
	DeletedAt       gorm.DeletedAt  `gorm:"column:deleted_at;type:datetime;index"`

	User User `gorm:"foreignKey:UserID;references:ID;constraint:OnDelete:CASCADE"`
}
