package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

func newTaskSSEHandlerTestContext(t *testing.T, method, path string) (*httptest.ResponseRecorder, *gin.Context) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(method, path, nil)
	c.Set("user_id", uint64(42))
	c.Set("user_uuid", "user-uuid")
	return w, c
}

func TestTaskSSEHandler_Stream_Success(t *testing.T) {
	broadcaster := service.NewTaskBroadcaster()
	taskSvc := &stubTaskService{
		getFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.TaskDTO, error) {
			return &service.TaskDTO{TaskID: taskUUID, Status: "running", Progress: 10}, nil
		},
	}
	h := NewTaskSSEHandler(taskSvc, broadcaster)
	w, c := newTaskSSEHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/task-uuid/events")
	c.Params = []gin.Param{{Key: "task_id", Value: "task-uuid"}}

	done := make(chan struct{})
	go func() {
		defer close(done)
		h.Stream(c)
	}()

	// Wait for subscription then emit a terminal event.
	time.Sleep(50 * time.Millisecond)
	broadcaster.Publish(context.Background(), "task-uuid", service.TaskEvent{
		EventType: "done",
		TaskID:    "task-uuid",
		Progress:  100,
		Status:    "completed",
	})

	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("handler did not finish")
	}

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "text/event-stream; charset=utf-8", w.Header().Get("Content-Type"))
	assert.Equal(t, "no-cache", w.Header().Get("Cache-Control"))

	body := w.Body.String()
	assert.Contains(t, body, "event: status")
	assert.Contains(t, body, `"progress":10`)
	assert.Contains(t, body, "event: done")
	assert.Contains(t, body, `"progress":100`)
	assert.Contains(t, body, `"status":"completed"`)
}

func TestTaskSSEHandler_Stream_NotFound(t *testing.T) {
	taskSvc := &stubTaskService{
		getFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.TaskDTO, error) {
			return nil, apperrors.NotFound("task")
		},
	}
	h := NewTaskSSEHandler(taskSvc, service.NewTaskBroadcaster())
	w, c := newTaskSSEHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/missing/events")
	c.Params = []gin.Param{{Key: "task_id", Value: "missing"}}

	h.Stream(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
	assert.Equal(t, "application/json; charset=utf-8", w.Header().Get("Content-Type"))
}
