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

type stubResultService struct {
	getResultFunc           func(ctx context.Context, userID uint64, taskUUID string) (*service.ResultSummary, error)
	getResultByResourceIDFunc func(ctx context.Context, userID uint64, resourceUUID string) (*service.ResultSummary, error)
}

func (s *stubResultService) GetResult(ctx context.Context, userID uint64, taskUUID string) (*service.ResultSummary, error) {
	if s.getResultFunc != nil {
		return s.getResultFunc(ctx, userID, taskUUID)
	}
	return nil, nil
}
func (s *stubResultService) GetResultByResourceID(ctx context.Context, userID uint64, resourceUUID string) (*service.ResultSummary, error) {
	if s.getResultByResourceIDFunc != nil {
		return s.getResultByResourceIDFunc(ctx, userID, resourceUUID)
	}
	return nil, nil
}

var _ service.ResultService = (*stubResultService)(nil)

func newResultHandlerTestContext(t *testing.T, method, path string, body *bytes.Buffer) (*httptest.ResponseRecorder, *gin.Context) {
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

func TestResultHandler_Get_Success(t *testing.T) {
	svc := &stubResultService{
		getResultFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.ResultSummary, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, "task-1", taskUUID)
			url := "https://minio/transcript.json?X-Amz-..."
			return &service.ResultSummary{
				TaskID: "task-1",
				Status: "completed",
				Files: service.ResultFiles{
					TranscriptURL: &url,
				},
				Metadata: map[string]interface{}{"duration": 3600.0},
			}, nil
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/task-1/result", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-1"}}

	h.Get(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "task-1", data["task_id"])
	files := data["files"].(map[string]any)
	assert.Equal(t, "https://minio/transcript.json?X-Amz-...", files["transcript_url"])
}

func TestResultHandler_Get_NotFound(t *testing.T) {
	svc := &stubResultService{
		getResultFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.ResultSummary, error) {
			return nil, apperrors.New(404, apperrors.CodeNotFound, "task not found")
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/missing/result", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "missing"}}

	h.Get(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeNotFound, errInfo["code"])
}

func TestResultHandler_Get_NotCompleted(t *testing.T) {
	svc := &stubResultService{
		getResultFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.ResultSummary, error) {
			return nil, apperrors.New(400, apperrors.CodeTaskNotCompleted, "task is not completed")
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/task-1/result", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-1"}}

	h.Get(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeTaskNotCompleted, errInfo["code"])
}

func TestResultHandler_Get_InternalError(t *testing.T) {
	svc := &stubResultService{
		getResultFunc: func(ctx context.Context, userID uint64, taskUUID string) (*service.ResultSummary, error) {
			return nil, errors.New("boom")
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/tasks/task-1/result", nil)
	c.Params = []gin.Param{{Key: "task_id", Value: "task-1"}}

	h.Get(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestResultHandler_GetByResourceID_Success(t *testing.T) {
	svc := &stubResultService{
		getResultByResourceIDFunc: func(ctx context.Context, userID uint64, resourceUUID string) (*service.ResultSummary, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, "res-1", resourceUUID)
			url := "https://minio/parsed.md?X-Amz-..."
			return &service.ResultSummary{
				TaskID: "task-7",
				Status: "completed",
				Files: service.ResultFiles{
					ParsedURL: &url,
				},
			}, nil
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/resources/res-1/result", nil)
	c.Params = []gin.Param{{Key: "id", Value: "res-1"}}

	h.GetByResourceID(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "task-7", data["task_id"])
	files := data["files"].(map[string]any)
	assert.Equal(t, "https://minio/parsed.md?X-Amz-...", files["parsed_url"])
}

func TestResultHandler_GetByResourceID_NotFound(t *testing.T) {
	svc := &stubResultService{
		getResultByResourceIDFunc: func(ctx context.Context, userID uint64, resourceUUID string) (*service.ResultSummary, error) {
			return nil, apperrors.New(404, apperrors.CodeNotFound, "resource not found")
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/resources/missing/result", nil)
	c.Params = []gin.Param{{Key: "resource_id", Value: "missing"}}

	h.GetByResourceID(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestResultHandler_GetByResourceID_NotCompleted(t *testing.T) {
	svc := &stubResultService{
		getResultByResourceIDFunc: func(ctx context.Context, userID uint64, resourceUUID string) (*service.ResultSummary, error) {
			return nil, apperrors.New(400, apperrors.CodeTaskNotCompleted, "task is not completed")
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/resources/res-1/result", nil)
	c.Params = []gin.Param{{Key: "id", Value: "res-1"}}

	h.GetByResourceID(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, apperrors.CodeTaskNotCompleted, errInfo["code"])
}

func TestResultHandler_GetByResourceID_InternalError(t *testing.T) {
	svc := &stubResultService{
		getResultByResourceIDFunc: func(ctx context.Context, userID uint64, resourceUUID string) (*service.ResultSummary, error) {
			return nil, errors.New("boom")
		},
	}
	h := NewResultHandler(svc)
	w, c := newResultHandlerTestContext(t, http.MethodGet, "/api/v1/resources/res-1/result", nil)
	c.Params = []gin.Param{{Key: "id", Value: "res-1"}}

	h.GetByResourceID(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
}
