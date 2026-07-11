package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// JWTAuth validates access tokens from the Authorization header.
func JWTAuth(jwtMgr *jwt.Manager) gin.HandlerFunc {
	return func(c *gin.Context) {
		token := extractBearerToken(c.GetHeader("Authorization"))
		if token == "" {
			response.Unauthorized(c, "AUTH_INVALID_TOKEN", "missing authorization header")
			c.Abort()
			return
		}

		claims, err := jwtMgr.ParseAccessToken(token)
		if err != nil {
			response.Unauthorized(c, "AUTH_INVALID_TOKEN", "access token invalid or expired")
			c.Abort()
			return
		}

		c.Set("user_uuid", claims.Subject)
		c.Set("user_id", claims.UserID)
		c.Set("email", claims.Email)
		c.Next()
	}
}

func extractBearerToken(authHeader string) string {
	parts := strings.SplitN(authHeader, " ", 2)
	if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
		return ""
	}
	return parts[1]
}

// InternalAuth validates the X-Internal-Key header for service-to-service calls.
func InternalAuth(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		key := c.GetHeader("X-Internal-Key")
		if key == "" {
			response.Unauthorized(c, "UNAUTHORIZED", "missing internal key")
			c.Abort()
			return
		}
		if key != cfg.AIService.InternalKey {
			response.Error(c, http.StatusForbidden, "FORBIDDEN", "invalid internal key")
			c.Abort()
			return
		}
		c.Next()
	}
}
