package service

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

func TestNewTaskDispatcher_DefaultTimeout(t *testing.T) {
	cfg := &config.Config{
		AIService: config.AIServiceConfig{BaseURL: "http://ai"},
		Task:      config.TaskConfig{},
		MinIO:     config.MinIOConfig{Bucket: "test-bucket"},
	}
	d := NewTaskDispatcher(cfg, zap.NewNop())
	httpD, ok := d.(*HTTPTaskDispatcher)
	require.True(t, ok)
	assert.Equal(t, 10*time.Second, httpD.dispatchTimeout)
	assert.Equal(t, "http://ai", httpD.baseURL)
	assert.Equal(t, "test-bucket", httpD.bucket)
}

func TestHTTPTaskDispatcher_Dispatch_NilTask(t *testing.T) {
	d := &HTTPTaskDispatcher{logger: zap.NewNop()}
	err := d.Dispatch(context.Background(), nil, &model.Resource{})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "task is nil")
}

func TestHTTPTaskDispatcher_Dispatch_MissingResource(t *testing.T) {
	d := &HTTPTaskDispatcher{logger: zap.NewNop()}
	err := d.Dispatch(context.Background(), &model.Task{UUID: "task-1"}, nil)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "task resource is missing")

	err = d.Dispatch(context.Background(), &model.Task{UUID: "task-1"}, &model.Resource{})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "task resource is missing")
}

func TestHTTPTaskDispatcher_Dispatch_UnsupportedType(t *testing.T) {
	d := &HTTPTaskDispatcher{logger: zap.NewNop()}
	err := d.Dispatch(context.Background(), &model.Task{UUID: "task-1", Type: "unknown"}, &model.Resource{UUID: "res-1"})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "unsupported task type")
}

func TestHTTPTaskDispatcher_Dispatch_MediaParseSuccess(t *testing.T) {
	var received map[string]any
	var headerKey string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/ai/v1/asr", r.URL.Path)
		headerKey = r.Header.Get("X-Internal-Key")
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &received)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()

	d := newTestDispatcher(server.URL, "secret-key")
	task := &model.Task{UUID: "task-1", Type: model.TaskTypeMediaParse}
	resource := &model.Resource{UUID: "res-1", StorageKey: "audio.mp3"}

	err := d.Dispatch(context.Background(), task, resource)
	require.NoError(t, err)
	assert.Equal(t, "secret-key", headerKey)
	assert.Equal(t, "task-1", received["task_id"])
	assert.Equal(t, "res-1", received["resource_id"])
	assert.Equal(t, "minio://test-bucket/audio.mp3", received["audio_url"])
	assert.Equal(t, "zh", received["language"])
	assert.Equal(t, "small", received["model"])
}

func TestHTTPTaskDispatcher_Dispatch_PdfParseSuccess(t *testing.T) {
	var received map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/ai/v1/pdf/parse", r.URL.Path)
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &received)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()

	d := newTestDispatcher(server.URL, "secret-key")
	task := &model.Task{UUID: "task-2", Type: model.TaskTypePdfParse}
	resource := &model.Resource{UUID: "res-2", StorageKey: "doc.pdf"}

	err := d.Dispatch(context.Background(), task, resource)
	require.NoError(t, err)
	assert.Equal(t, "task-2", received["task_id"])
	assert.Equal(t, "minio://test-bucket/doc.pdf", received["pdf_url"])
}

func TestHTTPTaskDispatcher_Dispatch_ClientError(t *testing.T) {
	d := newTestDispatcher("http://127.0.0.1:1", "key")
	task := &model.Task{UUID: "task-1", Type: model.TaskTypeMediaParse}
	resource := &model.Resource{UUID: "res-1", StorageKey: "audio.mp3"}

	err := d.Dispatch(context.Background(), task, resource)
	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, apperrors.CodeWorkerUnavailable, appErr.Code)
}

func TestHTTPTaskDispatcher_Dispatch_ServerError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer server.Close()

	d := newTestDispatcher(server.URL, "key")
	task := &model.Task{UUID: "task-1", Type: model.TaskTypeMediaParse}
	resource := &model.Resource{UUID: "res-1", StorageKey: "audio.mp3"}

	err := d.Dispatch(context.Background(), task, resource)
	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, apperrors.CodeWorkerUnavailable, appErr.Code)
}

func TestHTTPTaskDispatcher_Dispatch_RejectedError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
	}))
	defer server.Close()

	d := newTestDispatcher(server.URL, "key")
	task := &model.Task{UUID: "task-1", Type: model.TaskTypeMediaParse}
	resource := &model.Resource{UUID: "res-1", StorageKey: "audio.mp3"}

	err := d.Dispatch(context.Background(), task, resource)
	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, apperrors.CodeDispatchFailed, appErr.Code)
}

func newTestDispatcher(baseURL, key string) *HTTPTaskDispatcher {
	return &HTTPTaskDispatcher{
		client:          &http.Client{Timeout: 2 * time.Second},
		baseURL:         baseURL,
		internalKey:     key,
		bucket:          "test-bucket",
		dispatchTimeout: 2 * time.Second,
		logger:          zap.NewNop(),
	}
}
