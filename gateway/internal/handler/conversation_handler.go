package handler

import (
	"errors"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// ConversationHandler exposes REST endpoints for conversation and message persistence.
type ConversationHandler struct {
	svc service.ConversationService
}

// NewConversationHandler creates a ConversationHandler.
func NewConversationHandler(svc service.ConversationService) *ConversationHandler {
	return &ConversationHandler{svc: svc}
}

// CreateConversation handles POST /api/v1/conversations.
func (h *ConversationHandler) CreateConversation(c *gin.Context) {
	userID := c.GetUint64("user_id")
	var req service.CreateConversationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}
	conv, err := h.svc.Create(c.Request.Context(), userID, req)
	if err != nil {
		mapConversationError(c, err)
		return
	}
	c.JSON(http.StatusCreated, response.Envelope{
		Success: true,
		Data:    conv,
		Meta:    &response.MetaInfo{RequestID: c.GetString("request_id")},
	})
}

// ListConversations handles GET /api/v1/conversations.
func (h *ConversationHandler) ListConversations(c *gin.Context) {
	userID := c.GetUint64("user_id")
	page, limit, ok := parsePagination(c)
	if !ok {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid pagination parameters")
		return
	}
	conversations, total, err := h.svc.List(c.Request.Context(), userID, page, limit)
	if err != nil {
		mapConversationError(c, err)
		return
	}
	response.OKWithMeta(c, conversations, response.MetaInfo{
		Page:  page,
		Limit: limit,
		Total: total,
	})
}

// GetConversation handles GET /api/v1/conversations/:id.
func (h *ConversationHandler) GetConversation(c *gin.Context) {
	userID := c.GetUint64("user_id")
	id := c.Param("id")
	conv, err := h.svc.Get(c.Request.Context(), userID, id)
	if err != nil {
		mapConversationError(c, err)
		return
	}
	response.OK(c, conv)
}

// DeleteConversation handles DELETE /api/v1/conversations/:id.
func (h *ConversationHandler) DeleteConversation(c *gin.Context) {
	userID := c.GetUint64("user_id")
	id := c.Param("id")
	if err := h.svc.Delete(c.Request.Context(), userID, id); err != nil {
		mapConversationError(c, err)
		return
	}
	response.OK(c, gin.H{"deleted": true})
}

// ListMessages handles GET /api/v1/conversations/:id/messages.
func (h *ConversationHandler) ListMessages(c *gin.Context) {
	userID := c.GetUint64("user_id")
	id := c.Param("id")
	page, limit, ok := parsePagination(c)
	if !ok {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid pagination parameters")
		return
	}
	res, err := h.svc.ListMessages(c.Request.Context(), userID, id, page, limit)
	if err != nil {
		mapConversationError(c, err)
		return
	}
	response.OKWithMeta(c, res, response.MetaInfo{
		Page:  page,
		Limit: limit,
		Total: res.Total,
	})
}

// CreateMessage handles POST /api/v1/conversations/:id/messages.
func (h *ConversationHandler) CreateMessage(c *gin.Context) {
	userID := c.GetUint64("user_id")
	id := c.Param("id")
	var req service.CreateMessageRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, apperrors.CodeValidationError, "invalid request body")
		return
	}
	msg, err := h.svc.CreateMessage(c.Request.Context(), userID, id, req)
	if err != nil {
		mapConversationError(c, err)
		return
	}
	c.JSON(http.StatusCreated, response.Envelope{
		Success: true,
		Data:    msg,
		Meta:    &response.MetaInfo{RequestID: c.GetString("request_id")},
	})
}

func parsePagination(c *gin.Context) (int, int, bool) {
	page, err := strconv.Atoi(c.DefaultQuery("page", "1"))
	if err != nil || page <= 0 {
		return 0, 0, false
	}
	limit, err := strconv.Atoi(c.DefaultQuery("limit", "20"))
	if err != nil || limit <= 0 || limit > 100 {
		return 0, 0, false
	}
	return page, limit, true
}

func mapConversationError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
