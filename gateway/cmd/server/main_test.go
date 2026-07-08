package main

import (
	"context"
	"errors"
	"net/http"
	"syscall"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"go.uber.org/zap"
)

func TestBuildDependencies_NoConnections(t *testing.T) {
	cfg := &config.Config{
		App: config.AppConfig{Env: "test"},
		MySQL: config.MySQLConfig{
			Host: "127.0.0.1",
			Port: 1,
		},
		Redis: config.RedisConfig{
			Addr: "127.0.0.1:1",
		},
	}

	log := zap.NewNop()
	deps, db, redisClient := buildDependencies(cfg, log)

	assert.Nil(t, db)
	assert.Nil(t, redisClient)
	require.Len(t, deps, 2)
	assert.Equal(t, "mysql", deps[0].Name())
	assert.Equal(t, "redis", deps[1].Name())
	assert.Error(t, deps[0].Ping(context.Background()))
	assert.Error(t, deps[1].Ping(context.Background()))
}

func TestBuildDependencies_WithRedis(t *testing.T) {
	mr := miniredis.RunT(t)

	cfg := &config.Config{
		App: config.AppConfig{Env: "test"},
		MySQL: config.MySQLConfig{
			Host: "127.0.0.1",
			Port: 1,
		},
		Redis: config.RedisConfig{
			Addr: mr.Addr(),
		},
	}

	log := zap.NewNop()
	deps, db, redisClient := buildDependencies(cfg, log)

	assert.Nil(t, db)
	assert.NotNil(t, redisClient)
	require.Len(t, deps, 2)
	assert.NoError(t, deps[1].Ping(context.Background()))
}

func TestWaitForShutdown(t *testing.T) {
	srv := &http.Server{
		Addr:    ":18080",
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}),
	}

	serveErrCh := make(chan error, 1)
	go func() {
		serveErrCh <- srv.ListenAndServe()
	}()

	done := make(chan struct{})
	go func() {
		waitForShutdown(srv, zap.NewNop())
		close(done)
	}()

	// Give the server time to start before signaling.
	time.Sleep(100 * time.Millisecond)
	require.NoError(t, syscall.Kill(syscall.Getpid(), syscall.SIGTERM))

	select {
	case <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("shutdown did not complete in time")
	}

	// ListenAndServe will return http.ErrServerClosed after shutdown.
	assert.Eventually(t, func() bool {
		select {
		case err := <-serveErrCh:
			return errors.Is(err, http.ErrServerClosed)
		default:
			return false
		}
	}, 2*time.Second, 10*time.Millisecond)
}
