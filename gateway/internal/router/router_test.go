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

func TestHealthRoute(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	svc := service.NewHealthService("0.1.0")
	h := handler.NewHealthHandler(svc)

	r := New(cfg, logger, h, nil, nil, nil)

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

	r := New(cfg, logger, h, nil, nil, nil)
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

	r := New(cfg, logger, healthH, authH, nil, jwtMgr)

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

	r := New(cfg, logger, healthH, authH, fileH, jwtMgr)

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

func TestNoRoute_ReturnsNotFoundEnvelope(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	svc := service.NewHealthService("0.1.0")
	h := handler.NewHealthHandler(svc)

	r := New(cfg, logger, h, nil, nil, nil)

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
