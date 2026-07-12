package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/internal/handler"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"github.com/zhushuangquan/mkc/gateway/internal/router"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	"github.com/zhushuangquan/mkc/gateway/internal/storage"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	"github.com/zhushuangquan/mkc/gateway/pkg/logger"
	"go.uber.org/zap"
	"gorm.io/gorm"
)

func main() {
	cfgPath := os.Getenv("CONFIG_PATH")
	if cfgPath == "" {
		cfgPath = "config/config.yaml"
	}

	cfg, err := config.Load(cfgPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load config: %v\n", err)
		os.Exit(1)
	}

	appLogger, err := logger.New(cfg.Log.Level, cfg.Log.Format)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer func() { _ = appLogger.Sync() }()

	deps, db, redisClient := buildDependencies(cfg, appLogger)
	healthSvc := service.NewHealthService(cfg.App.Version, deps...)
	healthHandler := handler.NewHealthHandler(healthSvc)

	var authHandler *handler.AuthHandler
	var fileHandler *handler.FileHandler
	var taskHandler *handler.TaskHandler
	var internalTaskHandler *handler.InternalTaskHandler
	var taskSSEHandler *handler.TaskSSEHandler
	var resultHandler *handler.ResultHandler
	var qaSSEHandler *handler.QASSEHandler
	var convHandler *handler.ConversationHandler
	var summaryHandler *handler.SummaryHandler
	var jwtMgr *jwt.Manager
	if db != nil && redisClient != nil {
		userRepo := repository.NewUserRepository(db)
		resourceRepo := repository.NewResourceRepository(db)
		summaryRepo := repository.NewSummaryRepository(db)
		taskRepo := repository.NewTaskRepository(db)
		convRepo := repository.NewConversationRepository(db)
		msgRepo := repository.NewMessageRepository(db)
		tokenStore := repository.NewRedisTokenStore(redisClient)
		jwtMgr = jwt.NewManager(cfg.JWT.Secret, cfg.JWT.AccessTTL, cfg.JWT.RefreshTTL)
		authSvc := service.NewAuthService(userRepo, tokenStore, jwtMgr, &service.BcryptHasher{})
		authHandler = handler.NewAuthHandler(authSvc)

		taskBroadcaster := service.NewTaskBroadcaster()
		taskDispatcher := service.NewTaskDispatcher(cfg, appLogger)
		taskSvc := service.NewTaskService(appLogger, resourceRepo, taskRepo, taskBroadcaster, taskDispatcher, cfg.Task.RetryCooldown)
		taskHandler = handler.NewTaskHandler(taskSvc)
		internalTaskHandler = handler.NewInternalTaskHandler(taskSvc)
		taskSSEHandler = handler.NewTaskSSEHandler(taskSvc, taskBroadcaster)

		aiClient := service.NewAIClient(cfg)
		ctxWindow := service.NewContextWindowService(msgRepo, cfg.Conversation.MaxContextMessages, cfg.Conversation.MaxContextTokens)
		uow := repository.NewUnitOfWork(db)
		qaSvc := service.NewQAService(aiClient, convRepo, msgRepo, appLogger, service.WithContextWindowService(ctxWindow), service.WithUnitOfWork(uow))
		qaSSEHandler = handler.NewQASSEHandler(qaSvc)

		convSvc := service.NewConversationService(convRepo, msgRepo, resourceRepo, uow, cfg.Conversation.DefaultTitle, appLogger)
		convHandler = handler.NewConversationHandler(convSvc)
		summarySvc := service.NewSummaryService(appLogger, resourceRepo, summaryRepo, taskRepo, taskDispatcher)
		summaryHandler = handler.NewSummaryHandler(summarySvc)

		minioClient, err := storage.NewMinIOClient(cfg.MinIO)
		if err != nil {
			appLogger.Warn("minio connection failed", zap.Error(err))
		} else {
			resultsClient := minioClient.WithBucket(cfg.MinIO.ResultsBucket)
			resultSvc := service.NewResultService(appLogger, taskRepo, resultsClient, cfg.MinIO.PresignedExpiry, cfg.MinIO.ResultsBucket)
			resultHandler = handler.NewResultHandler(resultSvc)

			fileSvc := service.NewFileService(appLogger, minioClient, resourceRepo, taskRepo, taskDispatcher)
			fileHandler = handler.NewFileHandler(fileSvc)
		}
	}

	r := router.New(cfg, appLogger, healthHandler, authHandler, fileHandler, taskHandler, internalTaskHandler, taskSSEHandler, resultHandler, qaSSEHandler, convHandler, summaryHandler, jwtMgr)

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%d", cfg.Server.Port),
		Handler: r,
	}

	go func() {
		appLogger.Info("starting gateway", zap.String("addr", srv.Addr), zap.String("env", cfg.App.Env))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			appLogger.Fatal("failed to start server", zap.Error(err))
		}
	}()

	waitForShutdown(srv, appLogger)
}

func buildDependencies(cfg *config.Config, log *zap.Logger) ([]service.Dependency, *gorm.DB, *redis.Client) {
	var deps []service.Dependency
	var db *gorm.DB
	var redisClient *redis.Client

	db, err := repository.NewMySQL(cfg.MySQL)
	if err != nil {
		log.Warn("mysql connection failed", zap.Error(err))
		deps = append(deps, &service.NoopDependency{NameVal: "mysql"})
		db = nil
	} else {
		if err := repository.AutoMigrate(db); err != nil {
			log.Warn("auto migrate failed", zap.Error(err))
		}
		deps = append(deps, &repository.MySQLDependency{DB: db})
	}

	redisClient = repository.NewRedis(cfg.Redis)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := redisClient.Ping(ctx).Err(); err != nil {
		log.Warn("redis connection failed", zap.Error(err))
		_ = redisClient.Close()
		redisClient = nil
		deps = append(deps, &service.NoopDependency{NameVal: "redis"})
	} else {
		deps = append(deps, &repository.RedisDependency{Client: redisClient})
	}

	return deps, db, redisClient
}

func waitForShutdown(srv *http.Server, log *zap.Logger) {
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info("shutting down gateway")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Error("server shutdown failed", zap.Error(err))
	}
}
