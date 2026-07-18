package response

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestOK(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	OK(c, gin.H{"foo": "bar"})

	assert.Equal(t, http.StatusOK, w.Code)

	var body Envelope
	assert.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.True(t, body.Success)
	assert.NotNil(t, body.Data)
	assert.Nil(t, body.Error)
	assert.NotNil(t, body.Meta)
}

func TestErrorResponse(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	Error(c, http.StatusBadRequest, "BAD_REQUEST", "invalid input")

	assert.Equal(t, http.StatusBadRequest, w.Code)

	var body Envelope
	assert.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.False(t, body.Success)
	assert.Nil(t, body.Data)
	assert.Equal(t, "BAD_REQUEST", body.Error.Code)
	assert.Equal(t, "invalid input", body.Error.Message)
	assert.False(t, body.Error.Retryable)
	assert.Equal(t, "", body.Error.TraceID)
}

func TestErrorResponseRetryableWithTraceID(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Set("trace_id", "trace-1")

	Error(c, http.StatusGatewayTimeout, "LLM_TIMEOUT", "timeout")

	assert.Equal(t, http.StatusGatewayTimeout, w.Code)

	var body Envelope
	assert.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.Equal(t, "trace-1", body.Error.TraceID)
	assert.True(t, body.Error.Retryable)
}

func TestInternalError(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	InternalError(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)

	var body Envelope
	assert.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.False(t, body.Success)
	assert.Equal(t, "INTERNAL_ERROR", body.Error.Code)
}

func TestBadRequest(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	BadRequest(c, "VALIDATION_ERROR", "invalid")

	assert.Equal(t, http.StatusBadRequest, w.Code)

	var body Envelope
	assert.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.False(t, body.Success)
	assert.Equal(t, "VALIDATION_ERROR", body.Error.Code)
}

func TestUnauthorized(t *testing.T) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	Unauthorized(c, "UNAUTHORIZED", "missing token")

	assert.Equal(t, http.StatusUnauthorized, w.Code)

	var body Envelope
	assert.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.False(t, body.Success)
	assert.Equal(t, "UNAUTHORIZED", body.Error.Code)
}
