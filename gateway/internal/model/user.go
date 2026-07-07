package model

import (
	"time"

	"gorm.io/gorm"
)

// User represents a registered account.
type User struct {
	ID           uint64         `gorm:"column:id;primaryKey;autoIncrement"`
	UUID         string         `gorm:"column:uuid;type:char(36);uniqueIndex:uk_users_uuid;not null"`
	Email        string         `gorm:"column:email;type:varchar(255);uniqueIndex:uk_users_email;not null"`
	PasswordHash string         `gorm:"column:password_hash;type:varchar(255);not null"`
	Nickname     string         `gorm:"column:nickname;type:varchar(100)"`
	AvatarURL    string         `gorm:"column:avatar_url;type:varchar(512)"`
	Status       uint8          `gorm:"column:status;type:tinyint unsigned;default:1"`
	CreatedAt    time.Time      `gorm:"column:created_at;type:datetime(3);autoCreateTime"`
	UpdatedAt    time.Time      `gorm:"column:updated_at;type:datetime(3);autoUpdateTime"`
	DeletedAt    gorm.DeletedAt `gorm:"column:deleted_at;type:datetime(3);index"`
}
