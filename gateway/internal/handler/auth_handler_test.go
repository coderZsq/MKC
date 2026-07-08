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

type stubAuthService struct {
	registerFunc func(ctx context.Context, req service.RegisterRequest) (*service.AuthResponse, error)
	loginFunc    func(ctx context.Context, req service.LoginRequest) (*service.AuthResponse, error)
	refreshFunc  func(ctx context.Context, refreshToken string) (*service.RefreshResponse, error)
	logoutFunc   func(ctx context.Context, userUUID, refreshToken string) error
	meFunc       func(ctx context.Context, userUUID string) (*service.UserProfile, error)
}

func (s *stubAuthService) Register(ctx context.Context, req service.RegisterRequest) (*service.AuthResponse, error) {
	if s.registerFunc != nil {
		return s.registerFunc(ctx, req)
	}
	return nil, nil
}

func (s *stubAuthService) Login(ctx context.Context, req service.LoginRequest) (*service.AuthResponse, error) {
	if s.loginFunc != nil {
		return s.loginFunc(ctx, req)
	}
	return nil, nil
}

func (s *stubAuthService) Refresh(ctx context.Context, refreshToken string) (*service.RefreshResponse, error) {
	if s.refreshFunc != nil {
		return s.refreshFunc(ctx, refreshToken)
	}
	return nil, nil
}

func (s *stubAuthService) Logout(ctx context.Context, userUUID, refreshToken string) error {
	if s.logoutFunc != nil {
		return s.logoutFunc(ctx, userUUID, refreshToken)
	}
	return nil
}

func (s *stubAuthService) Me(ctx context.Context, userUUID string) (*service.UserProfile, error) {
	if s.meFunc != nil {
		return s.meFunc(ctx, userUUID)
	}
	return nil, nil
}

func TestAuthHandler_Register_Success(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		registerFunc: func(ctx context.Context, req service.RegisterRequest) (*service.AuthResponse, error) {
			return &service.AuthResponse{
				UserID:       "user-uuid",
				Email:        req.Email,
				Nickname:     req.Nickname,
				AccessToken:  "access-token",
				RefreshToken: "refresh-token",
				ExpiresIn:    900,
				TokenType:    "Bearer",
			}, nil
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{
		"email":    "alice@example.com",
		"password": "Password1",
		"nickname": "Alice",
	}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Register(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "user-uuid", data["user_id"])
	assert.Equal(t, "access-token", data["access_token"])
}

func TestAuthHandler_Register_ValidationError(t *testing.T) {
	gin.SetMode(gin.TestMode)

	h := NewAuthHandler(&stubAuthService{})

	body := map[string]string{
		"email": "not-email",
	}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Register(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
}

func TestAuthHandler_Register_Conflict(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		registerFunc: func(ctx context.Context, req service.RegisterRequest) (*service.AuthResponse, error) {
			return nil, &apperrors.AppError{Status: 409, Code: "CONFLICT", Message: "email already exists"}
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{
		"email":    "dupe@example.com",
		"password": "Password1",
	}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Register(c)

	assert.Equal(t, http.StatusConflict, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
}

func TestAuthHandler_Login_Success(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		loginFunc: func(ctx context.Context, req service.LoginRequest) (*service.AuthResponse, error) {
			return &service.AuthResponse{
				UserID:       "user-uuid",
				Email:        req.Email,
				AccessToken:  "access-token",
				RefreshToken: "refresh-token",
				ExpiresIn:    900,
				TokenType:    "Bearer",
			}, nil
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{
		"email":    "alice@example.com",
		"password": "Password1",
	}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Login(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
}

func TestAuthHandler_Login_Unauthorized(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		loginFunc: func(ctx context.Context, req service.LoginRequest) (*service.AuthResponse, error) {
			return nil, &apperrors.AppError{Status: 401, Code: "AUTH_INVALID_CREDENTIALS", Message: "email or password incorrect"}
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{
		"email":    "alice@example.com",
		"password": "wrong",
	}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Login(c)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
	err := resp["error"].(map[string]any)
	assert.Equal(t, "AUTH_INVALID_CREDENTIALS", err["code"])
}

func TestAuthHandler_Refresh_Success(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		refreshFunc: func(ctx context.Context, refreshToken string) (*service.RefreshResponse, error) {
			return &service.RefreshResponse{AccessToken: "new-access", ExpiresIn: 900, TokenType: "Bearer"}, nil
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{"refresh_token": "refresh-uuid"}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/refresh", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Refresh(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "new-access", data["access_token"])
}

func TestAuthHandler_Refresh_Invalid(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		refreshFunc: func(ctx context.Context, refreshToken string) (*service.RefreshResponse, error) {
			return nil, &apperrors.AppError{Status: 401, Code: "AUTH_SESSION_EXPIRED", Message: "session expired"}
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{"refresh_token": "bad"}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/refresh", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Refresh(c)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAuthHandler_Logout_Success(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		logoutFunc: func(ctx context.Context, userUUID, refreshToken string) error {
			assert.Equal(t, "user-uuid", userUUID)
			assert.Equal(t, "refresh-uuid", refreshToken)
			return nil
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{"refresh_token": "refresh-uuid"}
	jsonBody, _ := json.Marshal(body)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")
	c.Set("user_uuid", "user-uuid")

	h.Logout(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
}

func TestAuthHandler_Me_Success(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		meFunc: func(ctx context.Context, userUUID string) (*service.UserProfile, error) {
			return &service.UserProfile{UserID: userUUID, Email: "alice@example.com", Nickname: "Alice"}, nil
		},
	}
	h := NewAuthHandler(svc)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	c.Set("user_uuid", "user-uuid")

	h.Me(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
}

func TestAuthHandler_Login_BadRequest(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewAuthHandler(&stubAuthService{})

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader([]byte(`not json`)))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Login(c)
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestAuthHandler_Refresh_BadRequest(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewAuthHandler(&stubAuthService{})

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/refresh", bytes.NewReader([]byte(`not json`)))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Refresh(c)
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestAuthHandler_Logout_BadRequest(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewAuthHandler(&stubAuthService{})

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", bytes.NewReader([]byte(`not json`)))
	c.Request.Header.Set("Content-Type", "application/json")

	h.Logout(c)
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestAuthHandler_Logout_ServiceError(t *testing.T) {
	gin.SetMode(gin.TestMode)
	svc := &stubAuthService{
		logoutFunc: func(ctx context.Context, userUUID, refreshToken string) error {
			return &apperrors.AppError{Status: 500, Code: "INTERNAL", Message: "logout failed"}
		},
	}
	h := NewAuthHandler(svc)

	body := map[string]string{"refresh_token": "refresh-uuid"}
	jsonBody, _ := json.Marshal(body)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", bytes.NewReader(jsonBody))
	c.Request.Header.Set("Content-Type", "application/json")
	c.Set("user_uuid", "user-uuid")

	h.Logout(c)
	assert.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestAuthHandler_Me_NotFound(t *testing.T) {
	gin.SetMode(gin.TestMode)
	svc := &stubAuthService{
		meFunc: func(ctx context.Context, userUUID string) (*service.UserProfile, error) {
			return nil, &apperrors.AppError{Status: 404, Code: "NOT_FOUND", Message: "user not found"}
		},
	}
	h := NewAuthHandler(svc)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	c.Set("user_uuid", "missing-uuid")

	h.Me(c)
	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestAuthHandler_Me_Internal(t *testing.T) {
	gin.SetMode(gin.TestMode)
	svc := &stubAuthService{
		meFunc: func(ctx context.Context, userUUID string) (*service.UserProfile, error) {
			return nil, errors.New("boom")
		},
	}
	h := NewAuthHandler(svc)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	c.Set("user_uuid", "user-uuid")

	h.Me(c)
	assert.Equal(t, http.StatusInternalServerError, w.Code)
}
