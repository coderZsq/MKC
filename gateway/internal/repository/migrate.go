package repository

import (
	"fmt"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// AutoMigrate creates or updates all database tables.
func AutoMigrate(db *gorm.DB) error {
	if err := db.AutoMigrate(
		&model.User{},
		&model.Resource{},
		&model.Task{},
		&model.Conversation{},
		&model.Message{},
	); err != nil {
		return fmt.Errorf("failed to auto migrate: %w", err)
	}
	return nil
}

// DropAll removes all tables in reverse dependency order.
func DropAll(db *gorm.DB) error {
	if err := db.Migrator().DropTable(
		&model.Message{},
		&model.Conversation{},
		&model.Task{},
		&model.Resource{},
		&model.User{},
	); err != nil {
		return fmt.Errorf("failed to drop tables: %w", err)
	}
	return nil
}
