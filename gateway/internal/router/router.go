package router

import (
	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/internal/handler"
	"github.com/zhushuangquan/mkc/gateway/internal/middleware"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	"go.uber.org/zap"
)

// New creates and configures a Gin engine with middlewares and routes.
func New(cfg *config.Config, logger *zap.Logger, health *handler.HealthHandler, auth *handler.AuthHandler, file *handler.FileHandler, task *handler.TaskHandler, jwtMgr *jwt.Manager) *gin.Engine {
	mode := gin.ReleaseMode
	if cfg.Server.Mode == "debug" || cfg.Server.Mode == "" && cfg.App.Env == "dev" {
		mode = gin.DebugMode
	}
	gin.SetMode(mode)

	r := gin.New()
	r.MaxMultipartMemory = 32 << 20 // 32 MB

	r.Use(
		middleware.RequestID(),
		middleware.Recovery(logger),
		middleware.RequestLogger(logger),
		middleware.ErrorHandler(),
		middleware.CORS(),
	)

	r.GET("/health", health.Health)
	r.GET("/api/v1/health", health.Health)
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	if auth != nil && jwtMgr != nil {
		authLimit := middleware.NewRateLimiter(10, 60)
		api := r.Group("/api/v1")
		{
			authGroup := api.Group("/auth")
			authGroup.Use(authLimit.Limit())
			authGroup.POST("/register", auth.Register)
			authGroup.POST("/login", auth.Login)
			authGroup.POST("/refresh", auth.Refresh)
			authGroup.POST("/logout", auth.Logout)

			api.GET("/auth/me", middleware.JWTAuth(jwtMgr), auth.Me)

			if file != nil {
				api.POST("/files/upload", middleware.JWTAuth(jwtMgr), file.Upload)
			}

			if task != nil {
				api.GET("/tasks", middleware.JWTAuth(jwtMgr), task.List)
				api.GET("/tasks/:task_id", middleware.JWTAuth(jwtMgr), task.Get)
				api.POST("/tasks", middleware.JWTAuth(jwtMgr), task.Create)
			}
		}
	}

	r.NoRoute(func(c *gin.Context) {
		c.JSON(404, gin.H{
			"success": false,
			"data":    nil,
			"error": gin.H{
				"code":    "NOT_FOUND",
				"message": "resource not found",
			},
			"meta": nil,
		})
	})

	return r
}
