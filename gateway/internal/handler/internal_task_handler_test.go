package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

func TestInternalTaskHandler_UpdateProgress_Success(t *testing.T) {
	called := false
	svc := &stubTaskService{
		updateProgressFunc: func(ctx context.Context, taskUUID string, progress uint8) error {
			called = true
			assert.Equal(t, "task-uuid", taskUUID)
			assert.Equal(t, uint8(45), progress)
			return nil
		},
	}
	h := NewInternalTaskHandler(svc)
	w, c := newInternalTaskTestContext(t, http.MethodPatch, "/api/v1/internal/tasks/task-uuid/progress", bytes.NewBufferString(`{"progress":45}`))
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateProgress(c)

	assert.True(t, called)
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "task-uuid", data["task_id"])
	assert.Equal(t, float64(45), data["progress"])
}

func TestInternalTaskHandler_UpdateProgress_InvalidProgress(t *testing.T) {
	h := NewInternalTaskHandler(&stubTaskService{})
	body := bytes.NewBufferString(`{"progress":150}`)
	w, c := newInternalTaskTestContext(t, http.MethodPatch, "/api/v1/internal/tasks/task-uuid/progress", body)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateProgress(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeValidationError, errInfo["code"])
}

func TestInternalTaskHandler_UpdateProgress_NotFound(t *testing.T) {
	svc := &stubTaskService{
		updateProgressFunc: func(ctx context.Context, taskUUID string, progress uint8) error {
			return apperrors.NotFound("task")
		},
	}
	h := NewInternalTaskHandler(svc)
	body := bytes.NewBufferString(`{"progress":45}`)
	w, c := newInternalTaskTestContext(t, http.MethodPatch, "/api/v1/internal/tasks/task-uuid/progress", body)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateProgress(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestInternalTaskHandler_UpdateStatus_Running(t *testing.T) {
	called := false
	svc := &stubTaskService{
		markRunningFunc: func(ctx context.Context, taskUUID string) error {
			called = true
			assert.Equal(t, "task-uuid", taskUUID)
			return nil
		},
	}
	h := NewInternalTaskHandler(svc)
	body := bytes.NewBufferString(`{"status":"running"}`)
	w, c := newInternalTaskTestContext(t, http.MethodPost, "/api/v1/internal/tasks/task-uuid/status", body)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateStatus(c)

	assert.True(t, called)
	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "running", data["status"])
}

func TestInternalTaskHandler_UpdateStatus_Completed(t *testing.T) {
	called := false
	svc := &stubTaskService{
		markCompletedFunc: func(ctx context.Context, taskUUID string, result json.RawMessage) error {
			called = true
			assert.Equal(t, "task-uuid", taskUUID)
			assert.JSONEq(t, `{"text":"hello"}`, string(result))
			return nil
		},
	}
	h := NewInternalTaskHandler(svc)
	body := bytes.NewBufferString(`{"status":"completed","result":{"text":"hello"}}`)
	w, c := newInternalTaskTestContext(t, http.MethodPost, "/api/v1/internal/tasks/task-uuid/status", body)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateStatus(c)

	assert.True(t, called)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestInternalTaskHandler_UpdateStatus_Failed(t *testing.T) {
	called := false
	svc := &stubTaskService{
		markFailedFunc: func(ctx context.Context, taskUUID string, errMsg string) error {
			called = true
			assert.Equal(t, "task-uuid", taskUUID)
			assert.Equal(t, "processing failed", errMsg)
			return nil
		},
	}
	h := NewInternalTaskHandler(svc)
	body := bytes.NewBufferString(`{"status":"failed","error_message":"processing failed"}`)
	w, c := newInternalTaskTestContext(t, http.MethodPost, "/api/v1/internal/tasks/task-uuid/status", body)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateStatus(c)

	assert.True(t, called)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestInternalTaskHandler_UpdateStatus_InvalidStatus(t *testing.T) {
	h := NewInternalTaskHandler(&stubTaskService{})
	body := bytes.NewBufferString(`{"status":"paused"}`)
	w, c := newInternalTaskTestContext(t, http.MethodPost, "/api/v1/internal/tasks/task-uuid/status", body)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateStatus(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeValidationError, errInfo["code"])
}

func TestInternalTaskHandler_UpdateStatus_InvalidTransition(t *testing.T) {
	svc := &stubTaskService{
		markRunningFunc: func(ctx context.Context, taskUUID string) error {
			return apperrors.New(400, apperrors.CodeInvalidStateTransition, "cannot transition")
		},
	}
	h := NewInternalTaskHandler(svc)
	body := bytes.NewBufferString(`{"status":"running"}`)
	w, c := newInternalTaskTestContext(t, http.MethodPost, "/api/v1/internal/tasks/task-uuid/status", body)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	h.UpdateStatus(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeInvalidStateTransition, errInfo["code"])
}

func newInternalTaskTestContext(t *testing.T, method, path string, body *bytes.Buffer) (*httptest.ResponseRecorder, *gin.Context) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	if body == nil {
		body = &bytes.Buffer{}
	}
	c.Request = httptest.NewRequest(method, path, body)
	c.Request.Header.Set("Content-Type", "application/json")
	return w, c
}

// Ensure the stub is also a valid TaskService for the internal handler.
var _ service.TaskService = (*stubTaskService)(nil)
