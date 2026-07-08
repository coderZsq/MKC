package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
)

func TestJWTAuth_ValidToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)
	token, err := jwtMgr.GenerateAccessToken("user-uuid", "user@example.com", 42)
	require.NoError(t, err)

	r := gin.New()
	r.Use(JWTAuth(jwtMgr))
	r.GET("/protected", func(c *gin.Context) {
		assert.Equal(t, "user-uuid", c.GetString("user_uuid"))
		assert.Equal(t, uint64(42), c.GetUint64("user_id"))
		assert.Equal(t, "user@example.com", c.GetString("email"))
		c.Status(http.StatusOK)
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestJWTAuth_MissingHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)

	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)

	r := gin.New()
	r.Use(JWTAuth(jwtMgr))
	r.GET("/protected", func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.False(t, body["success"].(bool))
}

func TestJWTAuth_InvalidToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)

	r := gin.New()
	r.Use(JWTAuth(jwtMgr))
	r.GET("/protected", func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer invalid-token")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestJWTAuth_ExpiredToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	jwtMgr := jwt.NewManager("test-secret", -time.Hour, 24*time.Hour)
	token, err := jwtMgr.GenerateAccessToken("user-uuid", "user@example.com", 42)
	require.NoError(t, err)

	r := gin.New()
	r.Use(JWTAuth(jwtMgr))
	r.GET("/protected", func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestInternalAuth_ValidKey(t *testing.T) {
	cfg := &config.Config{
		AIService: config.AIServiceConfig{InternalKey: "valid-internal-key"},
	}

	r := gin.New()
	r.Use(InternalAuth(cfg))
	r.GET("/internal", func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/internal", nil)
	req.Header.Set("X-Internal-Key", "valid-internal-key")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestInternalAuth_MissingKey(t *testing.T) {
	cfg := &config.Config{
		AIService: config.AIServiceConfig{InternalKey: "valid-internal-key"},
	}

	r := gin.New()
	r.Use(InternalAuth(cfg))
	r.GET("/internal", func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/internal", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	errInfo := body["error"].(map[string]any)
	assert.Equal(t, "UNAUTHORIZED", errInfo["code"])
}

func TestInternalAuth_WrongKey(t *testing.T) {
	cfg := &config.Config{
		AIService: config.AIServiceConfig{InternalKey: "valid-internal-key"},
	}

	r := gin.New()
	r.Use(InternalAuth(cfg))
	r.GET("/internal", func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/internal", nil)
	req.Header.Set("X-Internal-Key", "wrong-key")
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusForbidden, w.Code)
	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	errInfo := body["error"].(map[string]any)
	assert.Equal(t, "FORBIDDEN", errInfo["code"])
}
