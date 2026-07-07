package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
	"go.uber.org/zap"
)

// Recovery recovers from panics and returns a generic 500 response.
func Recovery(logger *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if r := recover(); r != nil {
				logger.Error("panic recovered",
					zap.Any("error", r),
					zap.String("path", c.Request.URL.Path),
					zap.String("request_id", c.GetString(requestIDKey)),
				)
				response.InternalError(c)
				c.Abort()
			}
		}()
		c.Next()
	}
}
