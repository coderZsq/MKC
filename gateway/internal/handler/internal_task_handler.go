package handler

import (
	"encoding/json"
	"errors"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// InternalTaskHandler exposes service-to-service endpoints for workers to
// report task progress and status transitions.
type InternalTaskHandler struct {
	svc service.TaskService
}

// NewInternalTaskHandler creates an InternalTaskHandler.
func NewInternalTaskHandler(svc service.TaskService) *InternalTaskHandler {
	return &InternalTaskHandler{svc: svc}
}

// UpdateProgressRequest is the request body for PATCH /internal/tasks/:task_id/progress.
type UpdateProgressRequest struct {
	Progress uint8 `json:"progress" binding:"required,min=0,max=100"`
}

// UpdateStatusRequest is the request body for POST /internal/tasks/:task_id/status.
type UpdateStatusRequest struct {
	Status       string          `json:"status" binding:"required,oneof=running completed failed"`
	Result       json.RawMessage `json:"result,omitempty"`
	ErrorMessage string          `json:"error_message,omitempty"`
	AttemptCount *uint8          `json:"attempt_count,omitempty"`
}

// UpdateProgress updates the task progress percentage.
func (h *InternalTaskHandler) UpdateProgress(c *gin.Context) {
	taskUUID := c.Param("task_id")

	var req UpdateProgressRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}

	if err := h.svc.UpdateProgress(c.Request.Context(), taskUUID, req.Progress); err != nil {
		mapInternalTaskError(c, err)
		return
	}

	response.OK(c, gin.H{"task_id": taskUUID, "progress": req.Progress})
}

// UpdateStatus transitions the task status and optionally records the result, error, or attempt count.
func (h *InternalTaskHandler) UpdateStatus(c *gin.Context) {
	taskUUID := c.Param("task_id")

	var req UpdateStatusRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}

	update := service.InternalStatusUpdate{
		Status:       req.Status,
		Result:       req.Result,
		ErrorMessage: req.ErrorMessage,
		AttemptCount: req.AttemptCount,
	}
	if err := h.svc.ProcessInternalStatusUpdate(c.Request.Context(), taskUUID, update); err != nil {
		mapInternalTaskError(c, err)
		return
	}

	response.OK(c, gin.H{"task_id": taskUUID, "status": req.Status})
}

func mapInternalTaskError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
