package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/internal/handler"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"github.com/zhushuangquan/mkc/gateway/internal/router"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	"github.com/zhushuangquan/mkc/gateway/pkg/logger"
	"go.uber.org/zap"
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

	deps := buildDependencies(cfg, appLogger)
	healthSvc := service.NewHealthService(cfg.App.Version, deps...)
	healthHandler := handler.NewHealthHandler(healthSvc)

	r := router.New(cfg, appLogger, healthHandler)

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

func buildDependencies(cfg *config.Config, log *zap.Logger) []service.Dependency {
	var deps []service.Dependency

	db, err := repository.NewMySQL(cfg.MySQL)
	if err != nil {
		log.Warn("mysql connection failed", zap.Error(err))
		deps = append(deps, &service.NoopDependency{NameVal: "mysql"})
	} else {
		if err := repository.AutoMigrate(db); err != nil {
			log.Warn("auto migrate failed", zap.Error(err))
		}
		deps = append(deps, &repository.MySQLDependency{DB: db})
	}

	redisClient := repository.NewRedis(cfg.Redis)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := redisClient.Ping(ctx).Err(); err != nil {
		log.Warn("redis connection failed", zap.Error(err))
		_ = redisClient.Close()
		deps = append(deps, &service.NoopDependency{NameVal: "redis"})
	} else {
		deps = append(deps, &repository.RedisDependency{Client: redisClient})
	}

	return deps
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
