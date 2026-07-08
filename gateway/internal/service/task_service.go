package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"time"

	"github.com/google/uuid"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

const (
	defaultLimit = 20
	maxLimit     = 100
)

var allowedTaskTypes = map[string]bool{
	"media_parse":    true,
	"pdf_parse":      true,
	"document_parse": true,
}

// CreateTaskRequest represents a request to create a task for an existing resource.
type CreateTaskRequest struct {
	ResourceID string `json:"resource_id" binding:"required"`
	Type       string `json:"type"`
}

// TaskDTO is the task representation returned by the API.
type TaskDTO struct {
	TaskID       string          `json:"task_id"`
	ResourceID   string          `json:"resource_id"`
	ResourceName string          `json:"resource_name"`
	UserID       string          `json:"user_id,omitempty"`
	Type         string          `json:"type"`
	Status       string          `json:"status"`
	Progress     uint8           `json:"progress"`
	Result       json.RawMessage `json:"result,omitempty"`
	ErrorMessage string          `json:"error_message,omitempty"`
	StartedAt    *time.Time      `json:"started_at,omitempty"`
	CompletedAt  *time.Time      `json:"completed_at,omitempty"`
	CreatedAt    int64           `json:"created_at"`
	UpdatedAt    int64           `json:"updated_at"`
}

// ListTasksResult is returned by the task list operation.
type ListTasksResult struct {
	Tasks []TaskDTO
	Total int64
}

// TaskService defines task lifecycle operations.
// UpdateProgress and the Mark* transition methods are intended for internal
// worker use; they do not enforce row-level ownership checks.
type TaskService interface {
	Create(ctx context.Context, userID uint64, req CreateTaskRequest) (*TaskDTO, error)
	Get(ctx context.Context, userID uint64, taskUUID string) (*TaskDTO, error)
	List(ctx context.Context, userID uint64, page, limit int) (*ListTasksResult, error)
	UpdateProgress(ctx context.Context, taskUUID string, progress uint8) error
	MarkRunning(ctx context.Context, taskUUID string) error
	MarkCompleted(ctx context.Context, taskUUID string, result json.RawMessage) error
	MarkFailed(ctx context.Context, taskUUID string, errMsg string) error
}

// taskService is the concrete TaskService implementation.
type taskService struct {
	logger       *zap.Logger
	resourceRepo repository.ResourceRepository
	taskRepo     repository.TaskRepository
}

// NewTaskService creates a TaskService.
func NewTaskService(logger *zap.Logger, resourceRepo repository.ResourceRepository, taskRepo repository.TaskRepository) TaskService {
	if logger == nil {
		logger = zap.NewNop()
	}
	return &taskService{
		logger:       logger,
		resourceRepo: resourceRepo,
		taskRepo:     taskRepo,
	}
}

// Create creates a new task for an existing resource owned by the user.
func (s *taskService) Create(ctx context.Context, userID uint64, req CreateTaskRequest) (*TaskDTO, error) {
	if _, err := uuid.Parse(req.ResourceID); err != nil {
		return nil, apperrors.New(400, apperrors.CodeValidationError, "invalid resource_id")
	}
	if req.Type != "" && !allowedTaskTypes[req.Type] {
		return nil, apperrors.New(400, apperrors.CodeValidationError, "invalid task type")
	}

	resource, err := s.resourceRepo.GetByUUIDAndUserID(ctx, req.ResourceID, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.NotFound("resource")
		}
		s.logger.Error("failed to get resource for task creation", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	taskType := req.Type
	if taskType == "" {
		taskType = resource.Type
	}
	if taskType == "" {
		taskType = "document_parse"
	}

	task := &model.Task{
		UUID:       uuid.NewString(),
		ResourceID: resource.ID,
		UserID:     userID,
		Type:       taskType,
		Status:     model.TaskStatusPending,
		Progress:   0,
	}

	if err := s.taskRepo.Create(ctx, task); err != nil {
		s.logger.Error("failed to create task", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	dto := toTaskDTO(task)
	dto.ResourceID = resource.UUID
	dto.ResourceName = resource.Name
	return &dto, nil
}

// Get returns a task detail if it belongs to the user.
func (s *taskService) Get(ctx context.Context, userID uint64, taskUUID string) (*TaskDTO, error) {
	if _, err := uuid.Parse(taskUUID); err != nil {
		return nil, apperrors.New(400, apperrors.CodeValidationError, "invalid task_id")
	}

	task, err := s.taskRepo.GetByUUIDAndUserID(ctx, taskUUID, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.NotFound("task")
		}
		s.logger.Error("failed to get task", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}
	dto := toTaskDTO(task)
	return &dto, nil
}

// List returns paginated tasks for the user.
func (s *taskService) List(ctx context.Context, userID uint64, page, limit int) (*ListTasksResult, error) {
	if page < 1 {
		return nil, apperrors.New(400, apperrors.CodeValidationError, "page must be at least 1")
	}
	if limit < 1 {
		limit = defaultLimit
	}
	if limit > maxLimit {
		return nil, apperrors.New(400, apperrors.CodeValidationError, fmt.Sprintf("limit must not exceed %d", maxLimit))
	}

	tasks, total, err := s.taskRepo.ListByUserID(ctx, userID, page, limit)
	if err != nil {
		s.logger.Error("failed to list tasks", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	dtos := make([]TaskDTO, len(tasks))
	for i, t := range tasks {
		dtos[i] = toTaskDTO(&t)
	}
	return &ListTasksResult{Tasks: dtos, Total: total}, nil
}

// UpdateProgress updates the progress of a running task.
func (s *taskService) UpdateProgress(ctx context.Context, taskUUID string, progress uint8) error {
	if progress > 100 {
		return apperrors.New(400, apperrors.CodeValidationError, "progress must be between 0 and 100")
	}
	task, err := s.taskRepo.GetByUUID(ctx, taskUUID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return apperrors.NotFound("task")
		}
		s.logger.Error("failed to get task for progress update", zap.Error(err))
		return apperrors.Internal("internal server error")
	}
	if task.Status != model.TaskStatusRunning {
		return apperrors.New(400, apperrors.CodeValidationError, "task is not running")
	}
	return s.taskRepo.UpdateProgress(ctx, task.ID, progress)
}

// MarkRunning transitions a task from pending to running.
func (s *taskService) MarkRunning(ctx context.Context, taskUUID string) error {
	return s.transitionStatus(ctx, taskUUID, model.TaskStatusRunning, 0, nil, "")
}

// MarkCompleted transitions a task from running to completed.
func (s *taskService) MarkCompleted(ctx context.Context, taskUUID string, result json.RawMessage) error {
	return s.transitionStatus(ctx, taskUUID, model.TaskStatusCompleted, 100, result, "")
}

// MarkFailed transitions a task from running to failed.
func (s *taskService) MarkFailed(ctx context.Context, taskUUID string, errMsg string) error {
	return s.transitionStatus(ctx, taskUUID, model.TaskStatusFailed, 0, nil, errMsg)
}

func canTransition(from, to string) bool {
	switch from {
	case model.TaskStatusPending:
		return to == model.TaskStatusRunning
	case model.TaskStatusRunning:
		return to == model.TaskStatusCompleted || to == model.TaskStatusFailed
	case model.TaskStatusCompleted, model.TaskStatusFailed:
		return false
	}
	return false
}

func (s *taskService) transitionStatus(ctx context.Context, taskUUID, toStatus string, progress uint8, result json.RawMessage, errMsg string) error {
	task, err := s.taskRepo.GetByUUID(ctx, taskUUID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return apperrors.NotFound("task")
		}
		s.logger.Error("failed to get task for status transition", zap.Error(err))
		return apperrors.Internal("internal server error")
	}
	if !canTransition(task.Status, toStatus) {
		return apperrors.New(400, apperrors.CodeInvalidStateTransition, fmt.Sprintf("cannot transition from %s to %s", task.Status, toStatus))
	}
	return s.taskRepo.UpdateStatus(ctx, task.ID, toStatus, progress, result, errMsg)
}

func toTaskDTO(task *model.Task) TaskDTO {
	userID := ""
	if task.UserID != 0 {
		userID = strconv.FormatUint(task.UserID, 10)
	}

	resourceID := ""
	if task.Resource.UUID != "" {
		resourceID = task.Resource.UUID
	}

	return TaskDTO{
		TaskID:       task.UUID,
		ResourceID:   resourceID,
		ResourceName: task.Resource.Name,
		UserID:       userID,
		Type:         task.Type,
		Status:       task.Status,
		Progress:     task.Progress,
		Result:       task.Result,
		ErrorMessage: task.ErrorMessage,
		StartedAt:    task.StartedAt,
		CompletedAt:  task.CompletedAt,
		CreatedAt:    task.CreatedAt.Unix(),
		UpdatedAt:    task.UpdatedAt.Unix(),
	}
}
