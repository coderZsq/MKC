package repository

import (
	"context"
	"fmt"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// TaskRepository defines data access operations for tasks.
type TaskRepository interface {
	Create(ctx context.Context, t *model.Task) error
}

// GORMTaskRepository is a GORM-backed TaskRepository.
type GORMTaskRepository struct {
	db *gorm.DB
}

// NewTaskRepository creates a new GORM task repository.
func NewTaskRepository(db *gorm.DB) TaskRepository {
	return &GORMTaskRepository{db: db}
}

// Create inserts a new task record.
func (r *GORMTaskRepository) Create(ctx context.Context, task *model.Task) error {
	if err := r.db.WithContext(ctx).Create(task).Error; err != nil {
		return fmt.Errorf("failed to create task: %w", err)
	}
	return nil
}
