package router

import (
	"bytes"
	"context"
	"encoding/json"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/internal/handler"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	"go.uber.org/zap"
)

type stubAuthService struct{}

func (s *stubAuthService) Register(ctx context.Context, req service.RegisterRequest) (*service.AuthResponse, error) {
	return nil, nil
}
func (s *stubAuthService) Login(ctx context.Context, req service.LoginRequest) (*service.AuthResponse, error) {
	return nil, nil
}
func (s *stubAuthService) Refresh(ctx context.Context, refreshToken string) (*service.RefreshResponse, error) {
	return nil, nil
}
func (s *stubAuthService) Logout(ctx context.Context, userUUID, refreshToken string) error {
	return nil
}
func (s *stubAuthService) Me(ctx context.Context, userUUID string) (*service.UserProfile, error) {
	return nil, nil
}

type stubFileServiceForRouter struct{}

func (s *stubFileServiceForRouter) Upload(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error) {
	return &service.UploadResult{ResourceID: "r", TaskID: "t"}, nil
}

type stubTaskServiceForRouter struct{}

func (s *stubTaskServiceForRouter) Create(ctx context.Context, userID uint64, req service.CreateTaskRequest) (*service.TaskDTO, error) {
	return &service.TaskDTO{TaskID: "task-uuid", ResourceID: req.ResourceID}, nil
}

func (s *stubTaskServiceForRouter) Get(ctx context.Context, userID uint64, taskUUID string) (*service.TaskDTO, error) {
	return &service.TaskDTO{TaskID: taskUUID}, nil
}

func (s *stubTaskServiceForRouter) List(ctx context.Context, userID uint64, page, limit int) (*service.ListTasksResult, error) {
	return &service.ListTasksResult{Tasks: []service.TaskDTO{{TaskID: "task-uuid"}}, Total: 1}, nil
}

func (s *stubTaskServiceForRouter) UpdateProgress(ctx context.Context, taskUUID string, progress uint8) error {
	return nil
}
func (s *stubTaskServiceForRouter) MarkRunning(ctx context.Context, taskUUID string) error {
	return nil
}
func (s *stubTaskServiceForRouter) MarkCompleted(ctx context.Context, taskUUID string, result json.RawMessage) error {
	return nil
}
func (s *stubTaskServiceForRouter) MarkFailed(ctx context.Context, taskUUID string, errMsg string) error {
	return nil
}

var _ service.TaskService = (*stubTaskServiceForRouter)(nil)

type stubResultServiceForRouter struct{}

func (s *stubResultServiceForRouter) GetResult(ctx context.Context, userID uint64, taskUUID string) (*service.ResultSummary, error) {
	return nil, nil
}

var _ service.ResultService = (*stubResultServiceForRouter)(nil)

func TestHealthRoute(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	svc := service.NewHealthService("0.1.0")
	h := handler.NewHealthHandler(svc)

	r := New(cfg, logger, h, nil, nil, nil, nil, nil, nil, nil)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/api/v1/health", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestDebugMode(t *testing.T) {
	gin.SetMode(gin.ReleaseMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "dev"},
		Server: config.ServerConfig{Port: 8080, Mode: "debug"},
	}
	logger := zap.NewNop()
	svc := service.NewHealthService("0.1.0")
	h := handler.NewHealthHandler(svc)

	r := New(cfg, logger, h, nil, nil, nil, nil, nil, nil, nil)
	assert.NotNil(t, r)
}

func TestAuthRoutes_Registered(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	healthSvc := service.NewHealthService("0.1.0")
	healthH := handler.NewHealthHandler(healthSvc)
	authH := handler.NewAuthHandler(&stubAuthService{})
	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)

	r := New(cfg, logger, healthH, authH, nil, nil, nil, nil, nil, jwtMgr)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewBufferString("{invalid"))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestFileUploadRoute_Registered(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	healthSvc := service.NewHealthService("0.1.0")
	healthH := handler.NewHealthHandler(healthSvc)
	authH := handler.NewAuthHandler(&stubAuthService{})
	fileH := handler.NewFileHandler(&stubFileServiceForRouter{})
	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)

	r := New(cfg, logger, healthH, authH, fileH, nil, nil, nil, nil, jwtMgr)

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	part, err := writer.CreateFormFile("file", "hello.txt")
	require.NoError(t, err)
	_, err = part.Write([]byte("hello"))
	require.NoError(t, err)
	require.NoError(t, writer.Close())

	token, err := jwtMgr.GenerateAccessToken("user-uuid", "user@example.com", 42)
	require.NoError(t, err)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/v1/files/upload", &body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Set("Authorization", "Bearer "+token)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
}

func TestTaskRoutes_Registered(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	healthSvc := service.NewHealthService("0.1.0")
	healthH := handler.NewHealthHandler(healthSvc)
	authH := handler.NewAuthHandler(&stubAuthService{})
	taskH := handler.NewTaskHandler(&stubTaskServiceForRouter{})
	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)

	r := New(cfg, logger, healthH, authH, nil, taskH, nil, nil, nil, jwtMgr)

	token, err := jwtMgr.GenerateAccessToken("user-uuid", "user@example.com", 42)
	require.NoError(t, err)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/api/v1/tasks", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	meta, ok := resp["meta"].(map[string]any)
	require.True(t, ok)
	assert.Equal(t, float64(1), meta["page"])
}

func TestInternalRoutes_RegisteredAndProtected(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:       config.AppConfig{Env: "test"},
		Server:    config.ServerConfig{Port: 8080, Mode: "test"},
		AIService: config.AIServiceConfig{BaseURL: "http://localhost:5000", InternalKey: "internal-test-key"},
	}
	logger := zap.NewNop()
	authH := handler.NewAuthHandler(&stubAuthService{})
	taskH := handler.NewTaskHandler(&stubTaskServiceForRouter{})
	internalTaskH := handler.NewInternalTaskHandler(&stubTaskServiceForRouter{})
	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)
	r := New(cfg, logger, nil, authH, nil, taskH, internalTaskH, nil, nil, jwtMgr)

	// Missing key returns 401.
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPatch, "/api/v1/internal/tasks/task-uuid/progress", bytes.NewBufferString(`{"progress":45}`))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)

	// Wrong key returns 403.
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodPatch, "/api/v1/internal/tasks/task-uuid/progress", bytes.NewBufferString(`{"progress":45}`))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", "wrong-key")
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusForbidden, w.Code)

	// Valid key reaches the handler and returns 200.
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodPatch, "/api/v1/internal/tasks/task-uuid/progress", bytes.NewBufferString(`{"progress":45}`))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", "internal-test-key")
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestResultRoute_Registered(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	healthSvc := service.NewHealthService("0.1.0")
	healthH := handler.NewHealthHandler(healthSvc)
	authH := handler.NewAuthHandler(&stubAuthService{})
	taskH := handler.NewTaskHandler(&stubTaskServiceForRouter{})
	resultH := handler.NewResultHandler(&stubResultServiceForRouter{})
	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)

	r := New(cfg, logger, healthH, authH, nil, taskH, nil, nil, resultH, jwtMgr)

	token, err := jwtMgr.GenerateAccessToken("user-uuid", "user@example.com", 42)
	require.NoError(t, err)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/api/v1/tasks/task-uuid/result", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestNoRoute_ReturnsNotFoundEnvelope(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	svc := service.NewHealthService("0.1.0")
	h := handler.NewHealthHandler(svc)

	r := New(cfg, logger, h, nil, nil, nil, nil, nil, nil, nil)

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/not-a-real-path", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
	assert.Equal(t, "application/json; charset=utf-8", w.Header().Get("Content-Type"))

	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))

	assert.Equal(t, false, body["success"])
	assert.Nil(t, body["data"])
	assert.Nil(t, body["meta"])

	err, ok := body["error"].(map[string]any)
	require.True(t, ok)
	assert.Equal(t, "NOT_FOUND", err["code"])
	assert.Equal(t, "resource not found", err["message"])
}
