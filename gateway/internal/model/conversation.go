package model

import (
	"encoding/json"
	"time"
)

// Conversation represents a chat session owned by a user.
type Conversation struct {
	ID          uint64          `gorm:"column:id;primaryKey;autoIncrement"`
	UUID        string          `gorm:"column:uuid;type:char(36);uniqueIndex:uk_conversations_uuid;not null"`
	UserID      uint64          `gorm:"column:user_id;type:bigint unsigned;not null;index:idx_conversations_user_id"`
	Title       string          `gorm:"column:title;type:varchar(255)"`
	ResourceIDs json.RawMessage `gorm:"column:resource_ids;type:json"`
	ModelConfig json.RawMessage `gorm:"column:model_config;type:json"`
	CreatedAt   time.Time       `gorm:"column:created_at;type:datetime;autoCreateTime"`
	UpdatedAt   time.Time       `gorm:"column:updated_at;type:datetime;autoUpdateTime"`

	User User `gorm:"foreignKey:UserID;references:ID;constraint:OnDelete:CASCADE"`
}
