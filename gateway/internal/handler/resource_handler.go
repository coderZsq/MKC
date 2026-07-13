package handler

import (
	"errors"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// ResourceHandler exposes resource list endpoints.
type ResourceHandler struct {
	svc service.ResourceService
}

// NewResourceHandler creates a ResourceHandler.
func NewResourceHandler(svc service.ResourceService) *ResourceHandler {
	return &ResourceHandler{svc: svc}
}

// List returns the authenticated user's resources with summaries and tags.
func (h *ResourceHandler) List(c *gin.Context) {
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

	result, err := h.svc.List(c.Request.Context(), userID, service.ListResourcesRequest{
		Page:  page,
		Limit: limit,
		Tag:   c.Query("tag"),
	})
	if err != nil {
		mapResourceError(c, err)
		return
	}

	response.OKWithMeta(c, result.Items, response.MetaInfo{
		Page:  page,
		Limit: limit,
		Total: result.Total,
	})
}

func mapResourceError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
