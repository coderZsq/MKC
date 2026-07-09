package handler

import (
	"errors"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// ResultHandler exposes task result endpoints.
type ResultHandler struct {
	svc service.ResultService
}

// NewResultHandler creates a ResultHandler.
func NewResultHandler(svc service.ResultService) *ResultHandler {
	return &ResultHandler{svc: svc}
}

// Get returns the result summary and presigned URLs for a completed task.
func (h *ResultHandler) Get(c *gin.Context) {
	userID := c.GetUint64("user_id")
	taskUUID := c.Param("task_id")

	result, err := h.svc.GetResult(c.Request.Context(), userID, taskUUID)
	if err != nil {
		mapResultError(c, err)
		return
	}

	response.OK(c, result)
}

func mapResultError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
