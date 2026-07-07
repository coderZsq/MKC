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
