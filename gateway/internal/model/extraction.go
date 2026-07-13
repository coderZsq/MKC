package model

import "time"

// ResourceTag stores an extracted keyword tag for a resource.
type ResourceTag struct {
	ID         uint64    `gorm:"column:id;primaryKey;autoIncrement"`
	ResourceID uint64    `gorm:"column:resource_id;type:bigint unsigned;not null;uniqueIndex:uk_resource_tags_resource_tag;index:idx_resource_tags_resource_id"`
	Tag        string    `gorm:"column:tag;type:varchar(100);not null;uniqueIndex:uk_resource_tags_resource_tag;index:idx_resource_tags_tag"`
	Source     string    `gorm:"column:source;type:varchar(20);not null;default:llm"`
	CreatedAt  time.Time `gorm:"column:created_at;type:datetime;autoCreateTime"`
	UpdatedAt  time.Time `gorm:"column:updated_at;type:datetime;autoUpdateTime"`

	Resource Resource `gorm:"foreignKey:ResourceID;references:ID;constraint:OnDelete:CASCADE"`
}

// ResourceEntity stores an extracted named entity for a resource.
type ResourceEntity struct {
	ID         uint64    `gorm:"column:id;primaryKey;autoIncrement"`
	ResourceID uint64    `gorm:"column:resource_id;type:bigint unsigned;not null;uniqueIndex:uk_resource_entities_unique;index:idx_resource_entities_resource_id"`
	Entity     string    `gorm:"column:entity;type:varchar(255);not null;uniqueIndex:uk_resource_entities_unique"`
	Type       string    `gorm:"column:type;type:varchar(20);not null;uniqueIndex:uk_resource_entities_unique;index:idx_resource_entities_type"`
	Mention    string    `gorm:"column:mention;type:varchar(255);not null;uniqueIndex:uk_resource_entities_unique"`
	Source     string    `gorm:"column:source;type:varchar(20);not null;default:llm"`
	CreatedAt  time.Time `gorm:"column:created_at;type:datetime;autoCreateTime"`
	UpdatedAt  time.Time `gorm:"column:updated_at;type:datetime;autoUpdateTime"`

	Resource Resource `gorm:"foreignKey:ResourceID;references:ID;constraint:OnDelete:CASCADE"`
}
