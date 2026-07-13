package handler

import (
	"errors"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// ExtractionHandler exposes tag/entity endpoints.
type ExtractionHandler struct {
	svc service.ExtractionService
}

// NewExtractionHandler creates an ExtractionHandler.
func NewExtractionHandler(svc service.ExtractionService) *ExtractionHandler {
	return &ExtractionHandler{svc: svc}
}

// SaveInternal stores AI-generated tags and entities.
func (h *ExtractionHandler) SaveInternal(c *gin.Context) {
	resourceUUID := c.Param("id")
	var req service.SaveExtractionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}
	if err := h.svc.SaveInternal(c.Request.Context(), resourceUUID, req); err != nil {
		mapExtractionError(c, err)
		return
	}
	response.OK(c, gin.H{"resource_id": resourceUUID, "status": "saved"})
}

// Get returns extracted tags and entities for the current user.
func (h *ExtractionHandler) Get(c *gin.Context) {
	userID := c.GetUint64("user_id")
	resourceUUID := c.Param("id")
	result, err := h.svc.GetByResource(c.Request.Context(), userID, resourceUUID)
	if err != nil {
		mapExtractionError(c, err)
		return
	}
	response.OK(c, result)
}

func mapExtractionError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
