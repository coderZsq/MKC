package middleware

import (
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// JWTAuth validates access tokens and sets user context values.
// The token may be provided in the Authorization header as a Bearer token
// or in the `token` query parameter for SSE/EventSource clients.
func JWTAuth(jwtMgr *jwt.Manager) gin.HandlerFunc {
	return func(c *gin.Context) {
		token := extractBearerToken(c.GetHeader("Authorization"))
		if token == "" {
			token = c.Query("token")
		}
		if token == "" {
			response.Unauthorized(c, "AUTH_INVALID_TOKEN", "missing authorization header or token")
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
