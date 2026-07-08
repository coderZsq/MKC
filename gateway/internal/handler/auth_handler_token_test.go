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

func TestAuthHandler_Login_InvalidToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	svc := &stubAuthService{
		loginFunc: func(ctx context.Context, req service.LoginRequest) (*service.AuthResponse, error) {
			return nil, &apperrors.AppError{Status: 401, Code: "AUTH_INVALID_TOKEN", Message: "token invalid"}
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

	assert.Equal(t, http.StatusUnauthorized, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
	err := resp["error"].(map[string]any)
	assert.Equal(t, "AUTH_INVALID_TOKEN", err["code"])
}
