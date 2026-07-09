package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type stubTaskService struct {
	createFunc                    func(ctx context.Context, userID uint64, req service.CreateTaskRequest) (*service.TaskDTO, error)
	getFunc                       func(ctx context.Context, userID uint64, taskUUID string) (*service.TaskDTO, error)
	listFunc                      func(ctx context.Context, userID uint64, page, limit int) (*service.ListTasksResult, error)
	retryFunc                     func(ctx context.Context, userID uint64, taskUUID string) (*service.RetryResult, error)
	updateProgressFunc            func(ctx context.Context, taskUUID string, progress uint8) error
	processInternalStatusUpdateFunc func(ctx context.Context, taskUUID string, update service.InternalStatusUpdate) error
	markRunningFunc               func(ctx context.Context, taskUUID string) error
	markCompletedFunc             func(ctx context.Context, taskUUID string, result json.RawMessage) error
	markFailedFunc                func(ctx context.Context, taskUUID string, errMsg string) error
}

func (s *stubTaskService) Create(ctx context.Context, userID uint64, req service.CreateTaskRequest) (*service.TaskDTO, error) {
	if s.createFunc != nil {
		return s.createFunc(ctx, userID, req)
	}
	return nil, nil
}

func (s *stubTaskService) Get(ctx context.Context, userID uint64, taskUUID string) (*service.TaskDTO, error) {
	if s.getFunc != nil {
		return s.getFunc(ctx, userID, taskUUID)
	}
	return nil, nil
}

func (s *stubTaskService) List(ctx context.Context, userID uint64, page, limit int) (*service.ListTasksResult, error) {
	if s.listFunc != nil {
		return s.listFunc(ctx, userID, page, limit)
	}
	return nil, nil
}

func (s *stubTaskService) UpdateProgress(ctx context.Context, taskUUID string, progress uint8) error {
	if s.updateProgressFunc != nil {
		return s.updateProgressFunc(ctx, taskUUID, progress)
	}
	return nil
}

func (s *stubTaskService) Retry(ctx context.Context, userID uint64, taskUUID string) (*service.RetryResult, error) {
	if s.retryFunc != nil {
		return s.retryFunc(ctx, userID, taskUUID)
	}
	return nil, nil
}

func (s *stubTaskService) ProcessInternalStatusUpdate(ctx context.Context, taskUUID string, update service.InternalStatusUpdate) error {
	if s.processInternalStatusUpdateFunc != nil {
		return s.processInternalStatusUpdateFunc(ctx, taskUUID, update)
	}
	return nil
}

func (s *stubTaskService) MarkRunning(ctx context.Context, taskUUID string) error {
	if s.markRunningFunc != nil {
		return s.markRunningFunc(ctx, taskUUID)
	}
	return nil
}

func (s *stubTaskService) MarkCompleted(ctx context.Context, taskUUID string, result json.RawMessage) error {
	if s.markCompletedFunc != nil {
		return s.markCompletedFunc(ctx, taskUUID, result)
	}
	return nil
}

func (s *stubTaskService) MarkFailed(ctx context.Context, taskUUID string, errMsg string) error {
	if s.markFailedFunc != nil {
		return s.markFailedFunc(ctx, taskUUID, errMsg)
	}
	return nil
}

var _ service.TaskService = (*stubTaskService)(nil)

func newTaskHandlerTestContext(t *testing.T, method, path string, body *bytes.Buffer) (*httptest.ResponseRecorder, *gin.Context) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	if body == nil {
		body = &bytes.Buffer{}
	}
	c.Request = httptest.NewRequest(method, path, body)
	c.Set("user_id", uint64(42))
	c.Set("user_uuid", "user-uuid")
	return w, c
}

func TestTaskHandler_List_Success(t *testing.T) {
	svc := &stubTaskService{
		listFunc: func(ctx context.Context, userID uint64, page, limit int) (*service.ListTasksResult, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, 1, page)
			assert.Equal(t, 10, limit)
			return &service.ListTasksResult{
				Tasks: []service.TaskDTO{{TaskID: "t1"}},
				Total: 1,
			}, nil
		},
	}
	h := NewTaskHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/tasks?page=1&limit=10", nil)

	h.List(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	meta := resp["meta"].(map[string]any)
	assert.Equal(t, float64(1), meta["page"])
	assert.Equal(t, float64(10), meta["limit"])
	assert.Equal(t, float64(1), meta["total"])
}

func TestTaskHandler_List_Defaults(t *testing.T) {
	svc := &stubTaskService{
		listFunc: func(ctx context.Context, userID uint64, page, limit int) (*service.ListTasksResult, error) {
			assert.Equal(t, 1, page)
			assert.Equal(t, 20, limit)
			return &service.ListTasksResult{}, nil
		},
	}
	h := NewTaskHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/tasks", nil)

	h.List(c)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestTaskHandler_List_InvalidPage(t *testing.T) {
	h := NewTaskHandler(&stubTaskService{})
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/tasks?page=0", nil)

	h.List(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeValidationError, errInfo["code"])
}

func TestTaskHandler_List_InvalidLimit(t *testing.T) {
	h := NewTaskHandler(&stubTaskService{})
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/tasks?limit=200", nil)

	h.List(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestTaskHandler_Get_Success(t *testing.T) {
	svc := &stubTaskService{
		getFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.TaskDTO, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, "task-uuid", taskUUID)
			return &service.TaskDTO{TaskID: "task-uuid", Status: "pending"}, nil
		},
	}
	h := NewTaskHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/task-uuid", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.Get(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "task-uuid", data["task_id"])
}

func TestTaskHandler_Get_NotFound(t *testing.T) {
	svc := &stubTaskService{
		getFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.TaskDTO, error) {
			return nil, apperrors.NotFound("task")
		},
	}
	h := NewTaskHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/missing", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "missing"}}

	h.Get(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
}

func TestTaskHandler_Create_Success(t *testing.T) {
	svc := &stubTaskService{
		createFunc: func(ctx context.Context, userID uint64, req service.CreateTaskRequest) (*service.TaskDTO, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, "res-uuid", req.ResourceID)
			assert.Equal(t, "document_parse", req.Type)
			return &service.TaskDTO{TaskID: "task-uuid", ResourceID: "res-uuid", Status: "pending"}, nil
		},
	}
	h := NewTaskHandler(svc)
	body := bytes.NewBufferString(`{"resource_id":"res-uuid","type":"document_parse"}`)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/tasks", body)
	c.Request.Header.Set("Content-Type", "application/json")

	h.Create(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "task-uuid", data["task_id"])
}

func TestTaskHandler_Create_InvalidBody(t *testing.T) {
	h := NewTaskHandler(&stubTaskService{})
	body := bytes.NewBufferString(`{invalid`)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/tasks", body)
	c.Request.Header.Set("Content-Type", "application/json")

	h.Create(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
}

func TestTaskHandler_Create_MissingResourceID(t *testing.T) {
	h := NewTaskHandler(&stubTaskService{})
	body := bytes.NewBufferString(`{"type":"document_parse"}`)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/tasks", body)
	c.Request.Header.Set("Content-Type", "application/json")

	h.Create(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestTaskHandler_Create_ResourceNotFound(t *testing.T) {
	svc := &stubTaskService{
		createFunc: func(ctx context.Context, userID uint64, req service.CreateTaskRequest) (*service.TaskDTO, error) {
			return nil, apperrors.NotFound("resource")
		},
	}
	h := NewTaskHandler(svc)
	body := bytes.NewBufferString(`{"resource_id":"missing","type":"document_parse"}`)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/tasks", body)
	c.Request.Header.Set("Content-Type", "application/json")

	h.Create(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestTaskHandler_Create_InternalError(t *testing.T) {
	svc := &stubTaskService{
		createFunc: func(ctx context.Context, userID uint64, req service.CreateTaskRequest) (*service.TaskDTO, error) {
			return nil, errors.New("boom")
		},
	}
	h := NewTaskHandler(svc)
	body := bytes.NewBufferString(`{"resource_id":"res-uuid","type":"document_parse"}`)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/tasks", body)
	c.Request.Header.Set("Content-Type", "application/json")

	h.Create(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestTaskHandler_List_ServiceError(t *testing.T) {
	svc := &stubTaskService{
		listFunc: func(ctx context.Context, userID uint64, page, limit int) (*service.ListTasksResult, error) {
			return nil, errors.New("boom")
		},
	}
	h := NewTaskHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/tasks", nil)

	h.List(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestTaskHandler_Retry_Success(t *testing.T) {
	svc := &stubTaskService{
		retryFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.RetryResult, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, "task-uuid", taskUUID)
			return &service.RetryResult{TaskID: taskUUID, Status: "pending", AttemptCount: 0}, nil
		},
	}
	h := NewTaskHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/tasks/task-uuid/retry", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.Retry(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "pending", data["status"])
}

func TestTaskHandler_Retry_NotRetryable(t *testing.T) {
	svc := &stubTaskService{
		retryFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.RetryResult, error) {
			return nil, apperrors.TaskNotRetryable("current status cannot be retried")
		},
	}
	h := NewTaskHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/tasks/task-uuid/retry", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.Retry(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeTaskNotRetryable, errInfo["code"])
}
