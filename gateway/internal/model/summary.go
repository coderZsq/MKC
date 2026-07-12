package model

import (
	"encoding/json"
	"time"
)

// Summary stores full-document and section summaries for a resource.
type Summary struct {
	ID          uint64          `gorm:"column:id;primaryKey;autoIncrement"`
	ResourceID  uint64          `gorm:"column:resource_id;type:bigint unsigned;not null;index:idx_summaries_resource_type"`
	Type        string          `gorm:"column:type;type:varchar(20);not null;index:idx_summaries_resource_type"`
	Content     string          `gorm:"column:content;type:text;not null"`
	SectionMeta json.RawMessage `gorm:"column:section_meta;type:json"`
	Model       string          `gorm:"column:model;type:varchar(100)"`
	Tokens      int             `gorm:"column:tokens;type:int;default:0"`
	Fallback    bool            `gorm:"column:fallback;type:boolean;default:false"`
	CreatedAt   time.Time       `gorm:"column:created_at;type:datetime;autoCreateTime"`
	UpdatedAt   time.Time       `gorm:"column:updated_at;type:datetime;autoUpdateTime"`

	Resource Resource `gorm:"foreignKey:ResourceID;references:ID;constraint:OnDelete:CASCADE"`
}
