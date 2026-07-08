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
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
)

func TestJWTAuth_ValidToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)
	token, err := jwtMgr.GenerateAccessToken("user-uuid", "user@example.com")
	require.NoError(t, err)

	r := gin.New()
	r.Use(JWTAuth(jwtMgr))
	r.GET("/protected", func(c *gin.Context) {
		assert.Equal(t, "user-uuid", c.GetString("user_uuid"))
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
	token, err := jwtMgr.GenerateAccessToken("user-uuid", "user@example.com")
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
