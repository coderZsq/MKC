package response

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

const requestIDKey = "request_id"

// Envelope is the unified API response envelope.
type Envelope struct {
	Success bool       `json:"success"`
	Data    any        `json:"data"`
	Error   *ErrorInfo `json:"error"`
	Meta    *MetaInfo  `json:"meta"`
}

// ErrorInfo represents an API error payload.
type ErrorInfo struct {
	Code    string            `json:"code"`
	Message string            `json:"message"`
	Details map[string]string `json:"details,omitempty"`
}

// MetaInfo carries request metadata.
type MetaInfo struct {
	RequestID string    `json:"request_id"`
	Timestamp time.Time `json:"timestamp"`
	Page      int       `json:"page,omitempty"`
	Limit     int       `json:"limit,omitempty"`
	Total     int64     `json:"total,omitempty"`
}

// OK writes a successful response.
func OK(c *gin.Context, data any) {
	c.JSON(http.StatusOK, Envelope{
		Success: true,
		Data:    data,
		Meta:    buildMeta(c),
	})
}

// OKWithMeta writes a successful response with custom meta fields.
func OKWithMeta(c *gin.Context, data any, meta MetaInfo) {
	base := buildMeta(c)
	base.Page = meta.Page
	base.Limit = meta.Limit
	base.Total = meta.Total
	c.JSON(http.StatusOK, Envelope{
		Success: true,
		Data:    data,
		Meta:    base,
	})
}

// Error writes an error response with the provided HTTP status and error code.
func Error(c *gin.Context, status int, code, message string) {
	c.JSON(status, Envelope{
		Success: false,
		Error:   &ErrorInfo{Code: code, Message: message},
		Meta:    buildMeta(c),
	})
}

// BadRequest is a convenience helper for 400 errors.
func BadRequest(c *gin.Context, code, message string) {
	Error(c, http.StatusBadRequest, code, message)
}

// Unauthorized is a convenience helper for 401 errors.
func Unauthorized(c *gin.Context, code, message string) {
	Error(c, http.StatusUnauthorized, code, message)
}

// InternalError is a convenience helper for 500 errors.
func InternalError(c *gin.Context) {
	Error(c, http.StatusInternalServerError, "INTERNAL_ERROR", "internal server error")
}

func buildMeta(c *gin.Context) *MetaInfo {
	return &MetaInfo{
		RequestID: c.GetString(requestIDKey),
		Timestamp: time.Now().UTC(),
	}
}
