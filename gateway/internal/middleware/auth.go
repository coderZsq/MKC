package middleware

import (
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// JWTAuth validates access tokens and sets user context values.
func JWTAuth(jwtMgr *jwt.Manager) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Unauthorized(c, "AUTH_INVALID_TOKEN", "missing authorization header")
			c.Abort()
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			response.Unauthorized(c, "AUTH_INVALID_TOKEN", "invalid authorization header format")
			c.Abort()
			return
		}

		claims, err := jwtMgr.ParseAccessToken(parts[1])
		if err != nil {
			response.Unauthorized(c, "AUTH_INVALID_TOKEN", "access token invalid or expired")
			c.Abort()
			return
		}

		c.Set("user_uuid", claims.Subject)
		c.Set("email", claims.Email)
		c.Next()
	}
}
