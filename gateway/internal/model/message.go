package model

import (
	"encoding/json"
	"time"
)

// Message represents a single turn in a conversation.
type Message struct {
	ID              uint64          `gorm:"column:id;primaryKey;autoIncrement"`
	UUID            string          `gorm:"column:uuid;type:char(36);uniqueIndex:uk_messages_uuid;not null"`
	ConversationID  uint64          `gorm:"column:conversation_id;type:bigint unsigned;not null;index:idx_messages_conversation_id;index:idx_messages_conversation_created"`
	ParentMessageID *uint64         `gorm:"column:parent_message_id;type:bigint unsigned"`
	Role            string          `gorm:"column:role;type:varchar(20);not null"`
	Content         string          `gorm:"column:content;type:text;not null"`
	Reasoning       string          `gorm:"column:reasoning;type:text"`
	Citations       json.RawMessage `gorm:"column:citations;type:json"`
	TokenUsage      int             `gorm:"column:token_usage;type:int"`
	Model           string          `gorm:"column:model;type:varchar(100)"`
	CreatedAt       time.Time       `gorm:"column:created_at;type:datetime;autoCreateTime"`

	Conversation Conversation `gorm:"foreignKey:ConversationID;references:ID;constraint:OnDelete:CASCADE"`
}
