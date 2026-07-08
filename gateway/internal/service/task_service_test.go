package service

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

type stubResourceRepositoryForTask struct {
	createFunc           func(ctx context.Context, r *model.Resource) error
	updateStatusFunc     func(ctx context.Context, id uint64, status uint8) error
	getByUUIDAndUserFunc func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error)
}

func (r *stubResourceRepositoryForTask) Create(ctx context.Context, resource *model.Resource) error {
	if r.createFunc != nil {
		return r.createFunc(ctx, resource)
	}
	return nil
}

func (r *stubResourceRepositoryForTask) UpdateStatus(ctx context.Context, id uint64, status uint8) error {
	if r.updateStatusFunc != nil {
		return r.updateStatusFunc(ctx, id, status)
	}
	return nil
}

func (r *stubResourceRepositoryForTask) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
	if r.getByUUIDAndUserFunc != nil {
		return r.getByUUIDAndUserFunc(ctx, uuid, userID)
	}
	return nil, repository.ErrNotFound
}

var _ repository.ResourceRepository = (*stubResourceRepositoryForTask)(nil)

type stubTaskRepositoryForTask struct {
	createFunc         func(ctx context.Context, t *model.Task) error
	getByUUIDFunc      func(ctx context.Context, uuid string) (*model.Task, error)
	getByUUIDAndUserID func(ctx context.Context, uuid string, userID uint64) (*model.Task, error)
	listByUserIDFunc   func(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error)
	updateStatusFunc   func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error
	updateProgressFunc func(ctx context.Context, id uint64, progress uint8) error
}

func (r *stubTaskRepositoryForTask) Create(ctx context.Context, t *model.Task) error {
	if r.createFunc != nil {
		return r.createFunc(ctx, t)
	}
	return nil
}

func (r *stubTaskRepositoryForTask) GetByUUID(ctx context.Context, uuid string) (*model.Task, error) {
	if r.getByUUIDFunc != nil {
		return r.getByUUIDFunc(ctx, uuid)
	}
	return nil, repository.ErrNotFound
}

func (r *stubTaskRepositoryForTask) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
	if r.getByUUIDAndUserID != nil {
		return r.getByUUIDAndUserID(ctx, uuid, userID)
	}
	return nil, repository.ErrNotFound
}

func (r *stubTaskRepositoryForTask) ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error) {
	if r.listByUserIDFunc != nil {
		return r.listByUserIDFunc(ctx, userID, page, limit)
	}
	return nil, 0, nil
}

func (r *stubTaskRepositoryForTask) UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
	if r.updateStatusFunc != nil {
		return r.updateStatusFunc(ctx, id, status, progress, result, errMsg)
	}
	return nil
}

func (r *stubTaskRepositoryForTask) UpdateProgress(ctx context.Context, id uint64, progress uint8) error {
	if r.updateProgressFunc != nil {
		return r.updateProgressFunc(ctx, id, progress)
	}
	return nil
}

var _ repository.TaskRepository = (*stubTaskRepositoryForTask)(nil)

func newTestTaskService(t *testing.T) (*taskService, *stubResourceRepositoryForTask, *stubTaskRepositoryForTask) {
	resourceRepo := &stubResourceRepositoryForTask{}
	taskRepo := &stubTaskRepositoryForTask{}
	svc := NewTaskService(zap.NewNop(), resourceRepo, taskRepo).(*taskService)
	return svc, resourceRepo, taskRepo
}

func TestTaskService_Create_Success(t *testing.T) {
	svc, resourceRepo, taskRepo := newTestTaskService(t)

	resourceUUID := uuid.NewString()
	resourceRepo.getByUUIDAndUserFunc = func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
		return &model.Resource{ID: 1, UUID: uuid, Type: "media_parse"}, nil
	}
	taskRepo.createFunc = func(ctx context.Context, t *model.Task) error {
		t.ID = 10
		return nil
	}

	result, err := svc.Create(context.Background(), 42, CreateTaskRequest{ResourceID: resourceUUID, Type: "document_parse"})

	require.NoError(t, err)
	assert.Equal(t, resourceUUID, result.ResourceID)
	assert.Equal(t, "document_parse", result.Type)
	assert.Equal(t, model.TaskStatusPending, result.Status)
	assert.Equal(t, uint8(0), result.Progress)
	assert.Equal(t, "42", result.UserID)
}

func TestTaskService_Create_DefaultsToResourceType(t *testing.T) {
	svc, resourceRepo, _ := newTestTaskService(t)

	resourceUUID := uuid.NewString()
	resourceRepo.getByUUIDAndUserFunc = func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
		return &model.Resource{ID: 1, UUID: uuid, Type: "media_parse"}, nil
	}

	result, err := svc.Create(context.Background(), 42, CreateTaskRequest{ResourceID: resourceUUID})

	require.NoError(t, err)
	assert.Equal(t, "media_parse", result.Type)
}

func TestTaskService_Create_InvalidResourceID(t *testing.T) {
	svc, _, _ := newTestTaskService(t)

	_, err := svc.Create(context.Background(), 42, CreateTaskRequest{ResourceID: "not-a-uuid", Type: "document_parse"})

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
	assert.Equal(t, apperrors.CodeValidationError, appErr.Code)
}

func TestTaskService_Create_InvalidTaskType(t *testing.T) {
	svc, _, _ := newTestTaskService(t)

	_, err := svc.Create(context.Background(), 42, CreateTaskRequest{ResourceID: uuid.NewString(), Type: "unknown"})

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
	assert.Equal(t, apperrors.CodeValidationError, appErr.Code)
}

func TestTaskService_Create_ResourceNotFound(t *testing.T) {
	svc, resourceRepo, _ := newTestTaskService(t)
	resourceRepo.getByUUIDAndUserFunc = func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
		return nil, repository.ErrNotFound
	}

	_, err := svc.Create(context.Background(), 42, CreateTaskRequest{ResourceID: uuid.NewString()})

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusNotFound, appErr.Status)
	assert.Equal(t, apperrors.CodeNotFound, appErr.Code)
}

func TestTaskService_Get_Success(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)

	now := time.Now()
	taskUUID := uuid.NewString()
	taskRepo.getByUUIDAndUserID = func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
		return &model.Task{
			ID:         1,
			UUID:       uuid,
			UserID:     userID,
			ResourceID: 10,
			Resource:   model.Resource{UUID: "res-uuid"},
			Type:       "media_parse",
			Status:     model.TaskStatusRunning,
			Progress:   50,
			CreatedAt:  now,
			UpdatedAt:  now,
		}, nil
	}

	result, err := svc.Get(context.Background(), 42, taskUUID)

	require.NoError(t, err)
	assert.Equal(t, taskUUID, result.TaskID)
	assert.Equal(t, "res-uuid", result.ResourceID)
	assert.Equal(t, "42", result.UserID)
	assert.Equal(t, "running", result.Status)
	assert.Equal(t, uint8(50), result.Progress)
	assert.Equal(t, now.Unix(), result.CreatedAt)
}

func TestTaskService_Get_NotFound(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	taskRepo.getByUUIDAndUserID = func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
		return nil, repository.ErrNotFound
	}

	_, err := svc.Get(context.Background(), 42, uuid.NewString())

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusNotFound, appErr.Status)
}

func TestTaskService_List_Success(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)

	taskRepo.listByUserIDFunc = func(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error) {
		return []model.Task{
			{UUID: "t1", UserID: userID, Resource: model.Resource{UUID: "r1"}, Status: model.TaskStatusPending},
		}, 1, nil
	}

	result, err := svc.List(context.Background(), 42, 1, 10)

	require.NoError(t, err)
	assert.Len(t, result.Tasks, 1)
	assert.Equal(t, int64(1), result.Total)
	assert.Equal(t, "t1", result.Tasks[0].TaskID)
}

func TestTaskService_List_InvalidPage(t *testing.T) {
	svc, _, _ := newTestTaskService(t)

	_, err := svc.List(context.Background(), 42, 0, 10)

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
	assert.Equal(t, apperrors.CodeValidationError, appErr.Code)
}

func TestTaskService_List_InvalidLimit(t *testing.T) {
	svc, _, _ := newTestTaskService(t)

	_, err := svc.List(context.Background(), 42, 1, 101)

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
}

func TestTaskService_UpdateProgress_Success(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)

	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusRunning}, nil
	}
	var progress uint8
	taskRepo.updateProgressFunc = func(ctx context.Context, id uint64, p uint8) error {
		progress = p
		return nil
	}

	err := svc.UpdateProgress(context.Background(), "task-uuid", 75)

	require.NoError(t, err)
	assert.Equal(t, uint8(75), progress)
}

func TestTaskService_UpdateProgress_NotRunning(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusPending}, nil
	}

	err := svc.UpdateProgress(context.Background(), "task-uuid", 50)

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
}

func TestTaskService_MarkRunning_Success(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)

	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusPending}, nil
	}
	var called bool
	taskRepo.updateStatusFunc = func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
		called = true
		assert.Equal(t, model.TaskStatusRunning, status)
		assert.Equal(t, uint8(0), progress)
		return nil
	}

	err := svc.MarkRunning(context.Background(), "task-uuid")

	require.NoError(t, err)
	assert.True(t, called)
}

func TestTaskService_MarkRunning_InvalidTransition(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusCompleted}, nil
	}

	err := svc.MarkRunning(context.Background(), "task-uuid")

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
	assert.Equal(t, apperrors.CodeInvalidStateTransition, appErr.Code)
}

func TestTaskService_MarkCompleted_Success(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)

	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusRunning}, nil
	}
	var called bool
	taskRepo.updateStatusFunc = func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
		called = true
		assert.Equal(t, model.TaskStatusCompleted, status)
		assert.Equal(t, uint8(100), progress)
		assert.Equal(t, json.RawMessage(`{"ok":true}`), result)
		return nil
	}

	err := svc.MarkCompleted(context.Background(), "task-uuid", json.RawMessage(`{"ok":true}`))

	require.NoError(t, err)
	assert.True(t, called)
}

func TestTaskService_MarkFailed_Success(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)

	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusRunning}, nil
	}
	var called bool
	taskRepo.updateStatusFunc = func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
		called = true
		assert.Equal(t, model.TaskStatusFailed, status)
		assert.Equal(t, "boom", errMsg)
		return nil
	}

	err := svc.MarkFailed(context.Background(), "task-uuid", "boom")

	require.NoError(t, err)
	assert.True(t, called)
}

func TestTaskService_canTransition(t *testing.T) {
	assert.True(t, canTransition(model.TaskStatusPending, model.TaskStatusRunning))
	assert.True(t, canTransition(model.TaskStatusRunning, model.TaskStatusCompleted))
	assert.True(t, canTransition(model.TaskStatusRunning, model.TaskStatusFailed))
	assert.False(t, canTransition(model.TaskStatusCompleted, model.TaskStatusRunning))
	assert.False(t, canTransition(model.TaskStatusFailed, model.TaskStatusRunning))
	assert.False(t, canTransition(model.TaskStatusPending, model.TaskStatusCompleted))
}

func TestTaskService_toTaskDTO(t *testing.T) {
	now := time.Now()
	task := &model.Task{
		ID:         1,
		UUID:       uuid.NewString(),
		UserID:     42,
		ResourceID: 10,
		Resource:   model.Resource{UUID: "res-uuid"},
		Type:       "media_parse",
		Status:     model.TaskStatusPending,
		Progress:   0,
		CreatedAt:  now,
		UpdatedAt:  now,
	}

	dto := toTaskDTO(task)
	assert.Equal(t, task.UUID, dto.TaskID)
	assert.Equal(t, "res-uuid", dto.ResourceID)
	assert.Equal(t, "42", dto.UserID)
	assert.Equal(t, now.Unix(), dto.CreatedAt)
}
