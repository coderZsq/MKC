package handler

import (
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// AuthHandler exposes authentication endpoints.
type AuthHandler struct {
	svc service.AuthService
}

// NewAuthHandler creates an AuthHandler.
func NewAuthHandler(svc service.AuthService) *AuthHandler {
	return &AuthHandler{svc: svc}
}

// Register handles user registration.
func (h *AuthHandler) Register(c *gin.Context) {
	var req service.RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "VALIDATION_ERROR", "invalid request body")
		return
	}

	resp, err := h.svc.Register(c.Request.Context(), req)
	if err != nil {
		mapAuthError(c, err)
		return
	}

	response.OK(c, resp)
}

// Login handles user login.
func (h *AuthHandler) Login(c *gin.Context) {
	var req service.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "VALIDATION_ERROR", "invalid request body")
		return
	}

	resp, err := h.svc.Login(c.Request.Context(), req)
	if err != nil {
		mapAuthError(c, err)
		return
	}

	response.OK(c, resp)
}

// Refresh handles access token refresh.
func (h *AuthHandler) Refresh(c *gin.Context) {
	var req service.RefreshRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "VALIDATION_ERROR", "invalid request body")
		return
	}

	resp, err := h.svc.Refresh(c.Request.Context(), req.RefreshToken)
	if err != nil {
		mapAuthError(c, err)
		return
	}

	response.OK(c, resp)
}

// Logout handles user logout.
func (h *AuthHandler) Logout(c *gin.Context) {
	var req service.LogoutRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.BadRequest(c, "VALIDATION_ERROR", "invalid request body")
		return
	}

	userUUID := c.GetString("user_uuid")
	if err := h.svc.Logout(c.Request.Context(), userUUID, req.RefreshToken); err != nil {
		mapAuthError(c, err)
		return
	}

	response.OK(c, nil)
}

// Me returns the current authenticated user profile.
func (h *AuthHandler) Me(c *gin.Context) {
	userUUID := c.GetString("user_uuid")
	profile, err := h.svc.Me(c.Request.Context(), userUUID)
	if err != nil {
		mapAuthError(c, err)
		return
	}

	response.OK(c, profile)
}

func mapAuthError(c *gin.Context, err error) {
	if strings.Contains(err.Error(), "VALIDATION_ERROR") ||
		strings.Contains(err.Error(), "BAD_REQUEST") ||
		strings.Contains(err.Error(), "password must") {
		response.BadRequest(c, "VALIDATION_ERROR", err.Error())
		return
	}
	if strings.Contains(err.Error(), "CONFLICT") {
		c.JSON(http.StatusConflict, response.Envelope{
			Success: false,
			Error:   &response.ErrorInfo{Code: "CONFLICT", Message: err.Error()},
			Meta:    buildMeta(c),
		})
		return
	}
	if strings.Contains(err.Error(), "AUTH_INVALID_CREDENTIALS") {
		response.Unauthorized(c, "AUTH_INVALID_CREDENTIALS", "email or password incorrect")
		return
	}
	if strings.Contains(err.Error(), "AUTH_INVALID_TOKEN") {
		response.Unauthorized(c, "AUTH_INVALID_TOKEN", "access token invalid or expired")
		return
	}
	if strings.Contains(err.Error(), "AUTH_SESSION_EXPIRED") {
		response.Unauthorized(c, "AUTH_SESSION_EXPIRED", "session expired, please login again")
		return
	}
	if strings.Contains(err.Error(), "NOT_FOUND") {
		c.JSON(http.StatusNotFound, response.Envelope{
			Success: false,
			Error:   &response.ErrorInfo{Code: "NOT_FOUND", Message: err.Error()},
			Meta:    buildMeta(c),
		})
		return
	}
	response.InternalError(c)
}

func buildMeta(c *gin.Context) *response.MetaInfo {
	return &response.MetaInfo{
		RequestID: c.GetString("request_id"),
		Timestamp: time.Now().UTC(),
	}
}
