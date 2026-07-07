package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// HealthHandler exposes service health information.
type HealthHandler struct {
	svc *service.HealthService
}

// NewHealthHandler creates a health handler.
func NewHealthHandler(svc *service.HealthService) *HealthHandler {
	return &HealthHandler{svc: svc}
}

// Health returns the gateway health status.
func (h *HealthHandler) Health(c *gin.Context) {
	status, code := h.svc.Check(c.Request.Context())

	env := response.Envelope{
		Success: true,
		Data:    status,
	}

	c.JSON(code, env)
	if code != http.StatusOK {
		c.Abort()
	}
}
