package apperrors

import (
	"fmt"
	"net/http"
)

// AppError is a domain-aware error that maps to an HTTP response.
type AppError struct {
	Status  int
	Code    string
	Message string
}

func (e *AppError) Error() string {
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

// Common error codes used across the gateway.
const (
	CodeInternalError          = "INTERNAL_ERROR"
	CodeBadRequest             = "BAD_REQUEST"
	CodeValidationError        = "VALIDATION_ERROR"
	CodeUnauthorized           = "UNAUTHORIZED"
	CodeForbidden              = "FORBIDDEN"
	CodeNotFound               = "NOT_FOUND"
	CodeConflict               = "CONFLICT"
	CodeTooManyRequests        = "TOO_MANY_REQUESTS"
	CodeInvalidToken           = "AUTH_INVALID_TOKEN"
	CodeTokenExpired           = "AUTH_TOKEN_EXPIRED"
	CodeInvalidStateTransition = "INVALID_STATE_TRANSITION"
	CodeTaskNotCompleted       = "TASK_NOT_COMPLETED"
	CodePresignedURLFailed     = "PRESIGNED_URL_FAILED"
	CodeStorageError           = "STORAGE_ERROR"
)

// New creates a new AppError.
func New(status int, code, message string) *AppError {
	return &AppError{Status: status, Code: code, Message: message}
}

// Predefined helpers.
func BadRequest(message string) *AppError {
	return New(400, CodeBadRequest, message)
}

func Unauthorized(message string) *AppError {
	return New(401, CodeUnauthorized, message)
}

func Forbidden(message string) *AppError {
	return New(403, CodeForbidden, message)
}

func NotFound(resource string) *AppError {
	return New(404, CodeNotFound, resource+" not found")
}

func Conflict(message string) *AppError {
	return New(409, CodeConflict, message)
}

func Internal(message string) *AppError {
	return New(500, CodeInternalError, message)
}

func FileTooLarge(message string) *AppError {
	return New(http.StatusRequestEntityTooLarge, "FILE_TOO_LARGE", message)
}

func UnsupportedMediaType(message string) *AppError {
	return New(http.StatusUnsupportedMediaType, "FILE_UNSUPPORTED_TYPE", message)
}
