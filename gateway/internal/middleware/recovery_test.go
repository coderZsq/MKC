package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

func TestRecovery_ReturnsInternalErrorAndHidesPanic(t *testing.T) {
	gin.SetMode(gin.TestMode)

	logger := zap.NewNop()

	r := gin.New()
	r.Use(Recovery(logger))
	r.GET("/panic", func(c *gin.Context) {
		panic("something terrible happened")
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/panic", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusInternalServerError, w.Code)

	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))

	assert.Equal(t, false, body["success"])
	assert.Nil(t, body["data"])

	err, ok := body["error"].(map[string]any)
	require.True(t, ok)
	assert.Equal(t, "INTERNAL_ERROR", err["code"])
	assert.Equal(t, "internal server error", err["message"])

	// Ensure no panic details are leaked to the client.
	assert.NotContains(t, w.Body.String(), "something terrible happened")
}
