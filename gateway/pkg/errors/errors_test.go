package apperrors

import (
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestAppError(t *testing.T) {
	err := New(400, CodeBadRequest, "invalid input")
	assert.Equal(t, 400, err.Status)
	assert.Equal(t, CodeBadRequest, err.Code)
	assert.Equal(t, "invalid input", err.Message)
	assert.Equal(t, "BAD_REQUEST: invalid input", err.Error())
}

func TestHelpers(t *testing.T) {
	assert.Equal(t, CodeBadRequest, BadRequest("bad").Code)
	assert.Equal(t, http.StatusBadRequest, BadRequest("bad").Status)
	assert.Equal(t, CodeUnauthorized, Unauthorized("missing token").Code)
	assert.Equal(t, CodeForbidden, Forbidden("denied").Code)
	assert.Equal(t, http.StatusForbidden, Forbidden("denied").Status)
	assert.Equal(t, CodeNotFound, NotFound("user").Code)
	assert.Equal(t, CodeConflict, Conflict("duplicate").Code)
	assert.Equal(t, 409, Conflict("duplicate").Status)
	assert.Equal(t, 500, Internal("boom").Status)
	assert.Equal(t, "FILE_TOO_LARGE", FileTooLarge("too large").Code)
	assert.Equal(t, http.StatusRequestEntityTooLarge, FileTooLarge("too large").Status)
	assert.Equal(t, "FILE_UNSUPPORTED_TYPE", UnsupportedMediaType("bad type").Code)
	assert.Equal(t, http.StatusUnsupportedMediaType, UnsupportedMediaType("bad type").Status)
}
