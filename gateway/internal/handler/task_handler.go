package handler

import (
	"errors"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

const (
	defaultLimit = 20
	maxLimit     = 100
)

// TaskHandler exposes task management endpoints.
type TaskHandler struct {
	svc service.TaskService
}

// NewTaskHandler creates a TaskHandler.
func NewTaskHandler(svc service.TaskService) *TaskHandler {
	return &TaskHandler{svc: svc}
}

// List returns the authenticated user's tasks with pagination.
func (h *TaskHandler) List(c *gin.Context) {
	userID := c.GetUint64("user_id")
	page, ok := parsePage(c.DefaultQuery("page", "1"))
	if !ok {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid page parameter")
		return
	}
	limit, ok := parseLimit(c.DefaultQuery("limit", "20"))
	if !ok {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid limit parameter")
		return
	}

	result, err := h.svc.List(c.Request.Context(), userID, page, limit)
	if err != nil {
		mapTaskError(c, err)
		return
	}

	response.OKWithMeta(c, result.Tasks, response.MetaInfo{
		Page:  page,
		Limit: limit,
		Total: result.Total,
	})
}

// Get returns a single task by UUID if it belongs to the authenticated user.
func (h *TaskHandler) Get(c *gin.Context) {
	userID := c.GetUint64("user_id")
	taskUUID := c.Param("task_id")

	result, err := h.svc.Get(c.Request.Context(), userID, taskUUID)
	if err != nil {
		mapTaskError(c, err)
		return
	}

	response.OK(c, result)
}

// Create creates a new task for an existing resource owned by the user.
func (h *TaskHandler) Create(c *gin.Context) {
	userID := c.GetUint64("user_id")

	var req service.CreateTaskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}

	result, err := h.svc.Create(c.Request.Context(), userID, req)
	if err != nil {
		mapTaskError(c, err)
		return
	}

	response.OK(c, result)
}

// Retry resets and re-dispatches a failed or completed task.
func (h *TaskHandler) Retry(c *gin.Context) {
	userID := c.GetUint64("user_id")
	taskUUID := c.Param("task_id")

	result, err := h.svc.Retry(c.Request.Context(), userID, taskUUID)
	if err != nil {
		mapTaskError(c, err)
		return
	}

	response.OK(c, result)
}

func mapTaskError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}

func parsePage(value string) (int, bool) {
	page, err := strconv.Atoi(value)
	if err != nil || page < 1 {
		return 0, false
	}
	return page, true
}

func parseLimit(value string) (int, bool) {
	limit, err := strconv.Atoi(value)
	if err != nil {
		return defaultLimit, true
	}
	if limit < 1 {
		limit = defaultLimit
	}
	if limit > maxLimit {
		return 0, false
	}
	return limit, true
}
