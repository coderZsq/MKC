package repository

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// TaskRepository defines data access operations for tasks.
type TaskRepository interface {
	Create(ctx context.Context, t *model.Task) error
	GetByUUID(ctx context.Context, uuid string) (*model.Task, error)
	GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error)
	GetLatestCompletedByResourceID(ctx context.Context, resourceID uint64) (*model.Task, error)
	ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error)
	UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error
	UpdateStatusWithAttempt(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error
	UpdateProgress(ctx context.Context, id uint64, progress uint8) error
	ResetForRetry(ctx context.Context, id uint64) error
}

// GetLatestCompletedByResourceID returns the latest completed processing task for a resource.
func (r *GORMTaskRepository) GetLatestCompletedByResourceID(ctx context.Context, resourceID uint64) (*model.Task, error) {
	var task model.Task
	if err := r.db.WithContext(ctx).
		Preload("Resource").
		Where("resource_id = ? AND status = ?", resourceID, model.TaskStatusCompleted).
		Order("completed_at DESC, id DESC").
		First(&task).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get latest completed task by resource: %w", err)
	}
	return &task, nil
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

// GetByUUID fetches a task by its UUID.
func (r *GORMTaskRepository) GetByUUID(ctx context.Context, uuid string) (*model.Task, error) {
	var task model.Task
	if err := r.db.WithContext(ctx).Preload("Resource").Where("uuid = ?", uuid).First(&task).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get task by uuid: %w", err)
	}
	return &task, nil
}

// GetByUUIDAndUserID fetches a task by UUID and ensures it belongs to the user.
func (r *GORMTaskRepository) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
	var task model.Task
	if err := r.db.WithContext(ctx).Preload("Resource").Where("uuid = ? AND user_id = ?", uuid, userID).First(&task).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get task by uuid and user: %w", err)
	}
	return &task, nil
}

// ListByUserID returns paginated tasks for a user, ordered by newest first.
func (r *GORMTaskRepository) ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error) {
	var total int64
	if err := r.db.WithContext(ctx).Model(&model.Task{}).Where("user_id = ?", userID).Count(&total).Error; err != nil {
		return nil, 0, fmt.Errorf("failed to count tasks: %w", err)
	}

	offset := (page - 1) * limit
	var tasks []model.Task
	if err := r.db.WithContext(ctx).
		Preload("Resource").
		Where("user_id = ?", userID).
		Order("created_at DESC, id DESC").
		Limit(limit).
		Offset(offset).
		Find(&tasks).Error; err != nil {
		return nil, 0, fmt.Errorf("failed to list tasks: %w", err)
	}
	return tasks, total, nil
}

// UpdateStatus updates the task status and related fields in one call.
func (r *GORMTaskRepository) UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
	updates := map[string]any{
		"status":   status,
		"progress": progress,
		"result":   result,
	}
	if errMsg != "" {
		updates["error_message"] = errMsg
	}
	if status == model.TaskStatusRunning || status == model.TaskStatusCompleted || status == model.TaskStatusFailed {
		now := time.Now()
		if status == model.TaskStatusRunning {
			updates["started_at"] = now
		}
		if status == model.TaskStatusCompleted || status == model.TaskStatusFailed {
			updates["completed_at"] = now
		}
	}

	if err := r.db.WithContext(ctx).
		Model(&model.Task{}).
		Where("id = ?", id).
		Updates(updates).Error; err != nil {
		return fmt.Errorf("failed to update task status: %w", err)
	}
	return nil
}

// UpdateStatusWithAttempt updates the task status and records the current attempt count.
func (r *GORMTaskRepository) UpdateStatusWithAttempt(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error {
	updates := map[string]any{
		"status":      status,
		"progress":    progress,
		"result":      result,
		"retry_count": attemptCount,
	}
	if errMsg != "" {
		updates["error_message"] = errMsg
	}
	now := time.Now()
	if status == model.TaskStatusRunning {
		updates["started_at"] = now
	}
	if status == model.TaskStatusCompleted || status == model.TaskStatusFailed {
		updates["completed_at"] = now
	}

	if err := r.db.WithContext(ctx).
		Model(&model.Task{}).
		Where("id = ?", id).
		Updates(updates).Error; err != nil {
		return fmt.Errorf("failed to update task status with attempt: %w", err)
	}
	return nil
}

// ResetForRetry transitions a failed/completed task back to pending and clears prior result and error.
func (r *GORMTaskRepository) ResetForRetry(ctx context.Context, id uint64) error {
	updates := map[string]any{
		"status":        model.TaskStatusPending,
		"progress":      0,
		"retry_count":   0,
		"error_message": "",
		"result":        nil,
		"completed_at":  nil,
	}
	if err := r.db.WithContext(ctx).
		Model(&model.Task{}).
		Where("id = ?", id).
		Updates(updates).Error; err != nil {
		return fmt.Errorf("failed to reset task for retry: %w", err)
	}
	return nil
}

// UpdateProgress updates the task progress percentage.
func (r *GORMTaskRepository) UpdateProgress(ctx context.Context, id uint64, progress uint8) error {
	if err := r.db.WithContext(ctx).
		Model(&model.Task{}).
		Where("id = ?", id).
		Update("progress", progress).Error; err != nil {
		return fmt.Errorf("failed to update task progress: %w", err)
	}
	return nil
}
