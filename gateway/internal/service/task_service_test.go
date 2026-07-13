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
	createFunc              func(ctx context.Context, r *model.Resource) error
	updateStatusFunc        func(ctx context.Context, id uint64, status uint8) error
	getByUUIDAndUserFunc    func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error)
	countByUUIDsAndUserFunc func(ctx context.Context, uuids []string, userID uint64) (int64, error)
}

func (r *stubResourceRepositoryForTask) Create(ctx context.Context, resource *model.Resource) error {
	if r.createFunc != nil {
		return r.createFunc(ctx, resource)
	}
	return nil
}

func (r *stubResourceRepositoryForTask) GetByUUID(ctx context.Context, uuid string) (*model.Resource, error) {
	if r.getByUUIDAndUserFunc != nil {
		return r.getByUUIDAndUserFunc(ctx, uuid, 0)
	}
	return nil, repository.ErrNotFound
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

func (r *stubResourceRepositoryForTask) ListByUserID(ctx context.Context, userID uint64, page, limit int, tag string) ([]model.Resource, int64, error) {
	return nil, 0, nil
}

func (r *stubResourceRepositoryForTask) CountByUUIDsAndUserID(ctx context.Context, uuids []string, userID uint64) (int64, error) {
	if r.countByUUIDsAndUserFunc != nil {
		return r.countByUUIDsAndUserFunc(ctx, uuids, userID)
	}
	return int64(len(uuids)), nil
}

var _ repository.ResourceRepository = (*stubResourceRepositoryForTask)(nil)

type stubTaskRepositoryForTask struct {
	createFunc                  func(ctx context.Context, t *model.Task) error
	getByUUIDFunc               func(ctx context.Context, uuid string) (*model.Task, error)
	getByUUIDAndUserID          func(ctx context.Context, uuid string, userID uint64) (*model.Task, error)
	listByUserIDFunc            func(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error)
	updateStatusFunc            func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error
	updateStatusWithAttemptFunc func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error
	updateProgressFunc          func(ctx context.Context, id uint64, progress uint8) error
	resetForRetryFunc           func(ctx context.Context, id uint64) error
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

func (r *stubTaskRepositoryForTask) GetLatestCompletedByResourceID(ctx context.Context, resourceID uint64) (*model.Task, error) {
	return nil, repository.ErrNotFound
}

func (r *stubTaskRepositoryForTask) ListLatestByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64]model.Task, error) {
	return map[uint64]model.Task{}, nil
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

func (r *stubTaskRepositoryForTask) UpdateStatusWithAttempt(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error {
	if r.updateStatusWithAttemptFunc != nil {
		return r.updateStatusWithAttemptFunc(ctx, id, status, progress, result, errMsg, attemptCount)
	}
	return nil
}

func (r *stubTaskRepositoryForTask) ResetForRetry(ctx context.Context, id uint64) error {
	if r.resetForRetryFunc != nil {
		return r.resetForRetryFunc(ctx, id)
	}
	return nil
}

var _ repository.TaskRepository = (*stubTaskRepositoryForTask)(nil)

type fakeTaskDispatcher struct {
	calls           []dispatchCall
	summaryCalls    []summaryDispatchCall
	extractionCalls []extractionDispatchCall
}

type dispatchCall struct {
	Task     *model.Task
	Resource *model.Resource
}

type summaryDispatchCall struct {
	Resource *model.Resource
	Payload  SummaryDispatchPayload
}

type extractionDispatchCall struct {
	Resource *model.Resource
	Payload  ExtractionDispatchPayload
}

func (d *fakeTaskDispatcher) Dispatch(ctx context.Context, task *model.Task, resource *model.Resource) error {
	d.calls = append(d.calls, dispatchCall{Task: task, Resource: resource})
	return nil
}

func (d *fakeTaskDispatcher) DispatchSummary(ctx context.Context, resource *model.Resource, payload SummaryDispatchPayload) error {
	d.summaryCalls = append(d.summaryCalls, summaryDispatchCall{Resource: resource, Payload: payload})
	return nil
}

func (d *fakeTaskDispatcher) DispatchExtraction(ctx context.Context, resource *model.Resource, payload ExtractionDispatchPayload) error {
	d.extractionCalls = append(d.extractionCalls, extractionDispatchCall{Resource: resource, Payload: payload})
	return nil
}

func newTestTaskService(t *testing.T) (*taskService, *stubResourceRepositoryForTask, *stubTaskRepositoryForTask) {
	resourceRepo := &stubResourceRepositoryForTask{}
	taskRepo := &stubTaskRepositoryForTask{}
	svc := NewTaskService(zap.NewNop(), resourceRepo, taskRepo, nil, nil, 5*time.Minute).(*taskService)
	return svc, resourceRepo, taskRepo
}

func TestTaskService_Create_Success(t *testing.T) {
	svc, resourceRepo, taskRepo := newTestTaskService(t)

	resourceUUID := uuid.NewString()
	resourceRepo.getByUUIDAndUserFunc = func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
		return &model.Resource{ID: 1, UUID: uuid, Name: "test.pdf", Type: "media_parse"}, nil
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
		return &model.Resource{ID: 1, UUID: uuid, Name: "test.pdf", Type: "media_parse"}, nil
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
			Resource:   model.Resource{UUID: "res-uuid", Name: "test.pdf"},
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
			{UUID: "t1", UserID: userID, Resource: model.Resource{UUID: "r1", Name: "test.pdf"}, Status: model.TaskStatusPending},
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

func TestTaskService_CompletedAutoDispatchesSummary(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	dispatcher := &fakeTaskDispatcher{}
	svc.dispatcher = dispatcher
	resource := model.Resource{ID: 7, UUID: "res-1", Metadata: json.RawMessage(`{"auto_summary":true}`)}
	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{
			ID:       1,
			UUID:     uuid,
			Type:     model.TaskTypePdfParse,
			Status:   model.TaskStatusRunning,
			Resource: resource,
		}, nil
	}

	err := svc.MarkCompleted(context.Background(), "task-uuid", json.RawMessage(`{"pages":[{"text":"正文"}],"toc":[]}`))

	require.NoError(t, err)
	require.Len(t, dispatcher.summaryCalls, 1)
	assert.Equal(t, "res-1", dispatcher.summaryCalls[0].Resource.UUID)
	assert.Equal(t, "pdf", dispatcher.summaryCalls[0].Payload.SourceType)
	assert.Equal(t, "sum-res-1-auto", dispatcher.summaryCalls[0].Payload.TaskID)
	require.Len(t, dispatcher.extractionCalls, 1)
	assert.Equal(t, "res-1", dispatcher.extractionCalls[0].Resource.UUID)
	assert.Equal(t, "pdf", dispatcher.extractionCalls[0].Payload.SourceType)
	assert.Equal(t, "正文", dispatcher.extractionCalls[0].Payload.Content)
	assert.Equal(t, "tag-res-1-auto", dispatcher.extractionCalls[0].Payload.TaskID)
}

func TestTaskService_CompletedSkipsSummaryWhenDisabled(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	dispatcher := &fakeTaskDispatcher{}
	svc.dispatcher = dispatcher
	resource := model.Resource{ID: 7, UUID: "res-1", Metadata: json.RawMessage(`{"auto_summary":false}`)}
	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{
			ID:       1,
			UUID:     uuid,
			Type:     model.TaskTypePdfParse,
			Status:   model.TaskStatusRunning,
			Resource: resource,
		}, nil
	}

	err := svc.MarkCompleted(context.Background(), "task-uuid", json.RawMessage(`{"pages":[{"text":"正文"}],"toc":[]}`))

	require.NoError(t, err)
	assert.Empty(t, dispatcher.summaryCalls)
	require.Len(t, dispatcher.extractionCalls, 1)
	assert.Equal(t, "tag-res-1-auto", dispatcher.extractionCalls[0].Payload.TaskID)
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
	assert.True(t, canTransition(model.TaskStatusRunning, model.TaskStatusRunning))
	assert.True(t, canTransition(model.TaskStatusRunning, model.TaskStatusCompleted))
	assert.True(t, canTransition(model.TaskStatusRunning, model.TaskStatusFailed))
	assert.True(t, canTransition(model.TaskStatusFailed, model.TaskStatusRunning))
	assert.False(t, canTransition(model.TaskStatusCompleted, model.TaskStatusRunning))
	assert.False(t, canTransition(model.TaskStatusPending, model.TaskStatusCompleted))
}

func TestTaskService_toTaskDTO(t *testing.T) {
	now := time.Now()
	task := &model.Task{
		ID:         1,
		UUID:       uuid.NewString(),
		UserID:     42,
		ResourceID: 10,
		Resource:   model.Resource{UUID: "res-uuid", Name: "test.pdf"},
		Type:       "media_parse",
		Status:     model.TaskStatusPending,
		Progress:   0,
		CreatedAt:  now,
		UpdatedAt:  now,
	}

	dto := toTaskDTO(task)
	assert.Equal(t, task.UUID, dto.TaskID)
	assert.Equal(t, "res-uuid", dto.ResourceID)
	assert.Equal(t, "test.pdf", dto.ResourceName)
	assert.Equal(t, "42", dto.UserID)
	assert.Equal(t, now.Unix(), dto.CreatedAt)
}

type fakeTaskBroadcaster struct {
	events []TaskEvent
}

func (f *fakeTaskBroadcaster) Subscribe(ctx context.Context, taskID string) (<-chan TaskEvent, error) {
	return make(chan TaskEvent), nil
}

func (f *fakeTaskBroadcaster) Publish(ctx context.Context, taskID string, event TaskEvent) {
	f.events = append(f.events, event)
}

func (f *fakeTaskBroadcaster) Close(taskID string) {}

func TestTaskService_UpdateProgress_PublishesEvent(t *testing.T) {
	broadcaster := &fakeTaskBroadcaster{}
	svc := NewTaskService(zap.NewNop(), &stubResourceRepositoryForTask{}, &stubTaskRepositoryForTask{
		getByUUIDFunc: func(ctx context.Context, uuid string) (*model.Task, error) {
			return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusRunning}, nil
		},
		updateProgressFunc: func(ctx context.Context, id uint64, p uint8) error { return nil },
	}, broadcaster, nil, 0).(*taskService)

	err := svc.UpdateProgress(context.Background(), "task-uuid", 60)

	require.NoError(t, err)
	require.Len(t, broadcaster.events, 1)
	assert.Equal(t, "progress", broadcaster.events[0].EventType)
	assert.Equal(t, "running", broadcaster.events[0].Status)
	assert.Equal(t, uint8(60), broadcaster.events[0].Progress)
}

func TestTaskService_MarkRunning_PublishesStatusEvent(t *testing.T) {
	broadcaster := &fakeTaskBroadcaster{}
	svc := NewTaskService(zap.NewNop(), &stubResourceRepositoryForTask{}, &stubTaskRepositoryForTask{
		getByUUIDFunc: func(ctx context.Context, uuid string) (*model.Task, error) {
			return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusPending}, nil
		},
		updateStatusFunc: func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
			return nil
		},
	}, broadcaster, nil, 0).(*taskService)

	err := svc.MarkRunning(context.Background(), "task-uuid")

	require.NoError(t, err)
	require.Len(t, broadcaster.events, 1)
	assert.Equal(t, "status", broadcaster.events[0].EventType)
	assert.Equal(t, "running", broadcaster.events[0].Status)
}

func TestTaskService_MarkCompleted_PublishesDoneEvent(t *testing.T) {
	broadcaster := &fakeTaskBroadcaster{}
	svc := NewTaskService(zap.NewNop(), &stubResourceRepositoryForTask{}, &stubTaskRepositoryForTask{
		getByUUIDFunc: func(ctx context.Context, uuid string) (*model.Task, error) {
			return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusRunning}, nil
		},
		updateStatusFunc: func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
			return nil
		},
	}, broadcaster, nil, 0).(*taskService)

	err := svc.MarkCompleted(context.Background(), "task-uuid", json.RawMessage(`{"ok":true}`))

	require.NoError(t, err)
	require.Len(t, broadcaster.events, 1)
	assert.Equal(t, "done", broadcaster.events[0].EventType)
	assert.Equal(t, "completed", broadcaster.events[0].Status)
	assert.Equal(t, uint8(100), broadcaster.events[0].Progress)
}

func TestTaskService_MarkFailed_PublishesErrorEvent(t *testing.T) {
	broadcaster := &fakeTaskBroadcaster{}
	svc := NewTaskService(zap.NewNop(), &stubResourceRepositoryForTask{}, &stubTaskRepositoryForTask{
		getByUUIDFunc: func(ctx context.Context, uuid string) (*model.Task, error) {
			return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusRunning}, nil
		},
		updateStatusFunc: func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
			return nil
		},
	}, broadcaster, nil, 0).(*taskService)

	err := svc.MarkFailed(context.Background(), "task-uuid", "boom")

	require.NoError(t, err)
	require.Len(t, broadcaster.events, 1)
	assert.Equal(t, "error", broadcaster.events[0].EventType)
	assert.Equal(t, "failed", broadcaster.events[0].Status)
	require.NotNil(t, broadcaster.events[0].Message)
	assert.Equal(t, "boom", *broadcaster.events[0].Message)
}

func TestTaskService_Retry_Success(t *testing.T) {
	resourceRepo := &stubResourceRepositoryForTask{}
	taskRepo := &stubTaskRepositoryForTask{}
	dispatcher := &fakeTaskDispatcher{}
	now := time.Now().Add(-10 * time.Minute)
	taskUUID := uuid.NewString()
	resourceUUID := uuid.NewString()

	taskRepo.getByUUIDAndUserID = func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
		return &model.Task{
			ID:         1,
			UUID:       taskUUID,
			UserID:     userID,
			ResourceID: 10,
			Resource:   model.Resource{UUID: resourceUUID, Name: "test.pdf", StorageKey: "k"},
			Type:       model.TaskTypeMediaParse,
			Status:     model.TaskStatusFailed,
			RetryCount: 2,
			UpdatedAt:  now,
		}, nil
	}
	var resetCalled bool
	taskRepo.resetForRetryFunc = func(ctx context.Context, id uint64) error {
		resetCalled = true
		return nil
	}

	svc := NewTaskService(zap.NewNop(), resourceRepo, taskRepo, nil, dispatcher, 5*time.Minute).(*taskService)
	result, err := svc.Retry(context.Background(), 42, taskUUID)

	require.NoError(t, err)
	assert.Equal(t, taskUUID, result.TaskID)
	assert.Equal(t, model.TaskStatusPending, result.Status)
	assert.Equal(t, uint8(0), result.AttemptCount)
	assert.True(t, resetCalled)
	require.Len(t, dispatcher.calls, 1)
	assert.Equal(t, model.TaskTypeMediaParse, dispatcher.calls[0].Task.Type)
	assert.Equal(t, resourceUUID, dispatcher.calls[0].Resource.UUID)
}

func TestTaskService_Retry_NotAllowed(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	taskRepo.getByUUIDAndUserID = func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
		return &model.Task{UUID: uuid, UserID: userID, Status: model.TaskStatusRunning}, nil
	}

	_, err := svc.Retry(context.Background(), 42, uuid.NewString())

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
	assert.Equal(t, apperrors.CodeTaskNotRetryable, appErr.Code)
}

func TestTaskService_Retry_TooFrequent(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	taskRepo.getByUUIDAndUserID = func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
		return &model.Task{UUID: uuid, UserID: userID, Status: model.TaskStatusFailed, UpdatedAt: time.Now()}, nil
	}

	_, err := svc.Retry(context.Background(), 42, uuid.NewString())

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusTooManyRequests, appErr.Status)
	assert.Equal(t, apperrors.CodeRetryTooFrequent, appErr.Code)
}

func TestTaskService_ProcessInternalStatusUpdate_WithAttemptCount(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusRunning}, nil
	}
	var attempt uint8
	taskRepo.updateStatusWithAttemptFunc = func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, ac uint8) error {
		attempt = ac
		return nil
	}

	ac := uint8(2)
	err := svc.ProcessInternalStatusUpdate(context.Background(), "task-uuid", InternalStatusUpdate{Status: model.TaskStatusCompleted, Result: json.RawMessage(`{}`), AttemptCount: &ac})

	require.NoError(t, err)
	assert.Equal(t, uint8(2), attempt)
}

func TestTaskService_ProcessInternalStatusUpdate_FailedToRunning(t *testing.T) {
	svc, _, taskRepo := newTestTaskService(t)
	taskRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.Task, error) {
		return &model.Task{ID: 1, UUID: uuid, Status: model.TaskStatusFailed}, nil
	}
	var status string
	taskRepo.updateStatusFunc = func(ctx context.Context, id uint64, s string, progress uint8, result json.RawMessage, errMsg string) error {
		status = s
		return nil
	}

	err := svc.ProcessInternalStatusUpdate(context.Background(), "task-uuid", InternalStatusUpdate{Status: model.TaskStatusRunning})

	require.NoError(t, err)
	assert.Equal(t, model.TaskStatusRunning, status)
}

func TestTaskService_Create_AutoDispatch(t *testing.T) {
	resourceRepo := &stubResourceRepositoryForTask{}
	taskRepo := &stubTaskRepositoryForTask{}
	dispatcher := &fakeTaskDispatcher{}
	resourceUUID := uuid.NewString()

	resourceRepo.getByUUIDAndUserFunc = func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
		return &model.Resource{ID: 1, UUID: uuid, Name: "test.mp3", Type: model.TaskTypeMediaParse}, nil
	}
	taskRepo.createFunc = func(ctx context.Context, t *model.Task) error {
		t.ID = 10
		return nil
	}

	svc := NewTaskService(zap.NewNop(), resourceRepo, taskRepo, nil, dispatcher, 0).(*taskService)
	_, err := svc.Create(context.Background(), 42, CreateTaskRequest{ResourceID: resourceUUID})

	require.NoError(t, err)
	require.Len(t, dispatcher.calls, 1)
	assert.Equal(t, model.TaskTypeMediaParse, dispatcher.calls[0].Task.Type)
}
