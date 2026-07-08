package apperrors

import (
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
	assert.Equal(t, CodeNotFound, NotFound("user").Code)
	assert.Equal(t, CodeUnauthorized, Unauthorized("missing token").Code)
	assert.Equal(t, CodeConflict, Conflict("duplicate").Code)
	assert.Equal(t, 409, Conflict("duplicate").Status)
	assert.Equal(t, 500, Internal("boom").Status)
}
