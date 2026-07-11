package handler

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// AskRequest is the request body for POST /api/v1/conversations/:id/ask.
type AskRequest struct {
	Question string `json:"question" binding:"required,max=2000"`
}

// QASSEHandler exposes the Server-Sent Events endpoint for Q&A.
type QASSEHandler struct {
	qaSvc service.QAService
}

// NewQASSEHandler creates a QASSEHandler.
func NewQASSEHandler(qaSvc service.QAService) *QASSEHandler {
	return &QASSEHandler{qaSvc: qaSvc}
}

// Ask handles a question and streams the answer as Server-Sent Events.
func (h *QASSEHandler) Ask(c *gin.Context) {
	userID := c.GetUint64("user_id")
	userUUID := c.GetString("user_uuid")
	conversationUUID := c.Param("id")

	var req AskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}

	events, err := h.qaSvc.Ask(c.Request.Context(), userID, userUUID, conversationUUID, req.Question)
	if err != nil {
		mapQAError(c, err)
		return
	}

	flusher, ok := c.Writer.(http.Flusher)
	if !ok {
		response.InternalError(c)
		return
	}

	c.Header("Content-Type", "text/event-stream; charset=utf-8")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")
	c.Status(http.StatusOK)
	flusher.Flush()

	for ev := range events {
		if _, err := c.Writer.Write([]byte(ev.Raw)); err != nil {
			return
		}
		flusher.Flush()
	}
}

func mapQAError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		if appErr.Code == "CONVERSATION_NOT_FOUND" {
			response.Error(c, http.StatusNotFound, appErr.Code, appErr.Message)
			return
		}
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
