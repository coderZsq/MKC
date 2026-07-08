package router

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/internal/handler"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	"go.uber.org/zap"
)

func TestNoRoute_ReturnsNotFoundEnvelope(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		App:    config.AppConfig{Env: "test"},
		Server: config.ServerConfig{Port: 8080, Mode: "test"},
	}
	logger := zap.NewNop()
	svc := service.NewHealthService("0.1.0")
	h := handler.NewHealthHandler(svc)

	r := New(cfg, logger, h)

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
