package handler

import (
	"errors"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// SummaryHandler exposes summary endpoints.
type SummaryHandler struct {
	svc service.SummaryService
}

// NewSummaryHandler creates a SummaryHandler.
func NewSummaryHandler(svc service.SummaryService) *SummaryHandler {
	return &SummaryHandler{svc: svc}
}

// SaveInternal stores AI-generated summaries.
func (h *SummaryHandler) SaveInternal(c *gin.Context) {
	resourceUUID := c.Param("id")
	var req service.SaveSummaryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}
	if err := h.svc.SaveInternal(c.Request.Context(), resourceUUID, req); err != nil {
		mapSummaryError(c, err)
		return
	}
	response.OK(c, gin.H{"resource_id": resourceUUID, "status": "saved"})
}

// Get returns a resource summary for the current user.
func (h *SummaryHandler) Get(c *gin.Context) {
	userID := c.GetUint64("user_id")
	resourceUUID := c.Param("id")
	result, err := h.svc.GetByResource(c.Request.Context(), userID, resourceUUID)
	if err != nil {
		mapSummaryError(c, err)
		return
	}
	response.OK(c, result)
}

// Trigger queues summary generation for a processed resource.
func (h *SummaryHandler) Trigger(c *gin.Context) {
	userID := c.GetUint64("user_id")
	resourceUUID := c.Param("id")
	result, err := h.svc.Trigger(c.Request.Context(), userID, resourceUUID)
	if err != nil {
		mapSummaryError(c, err)
		return
	}
	response.OK(c, result)
}

func mapSummaryError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
