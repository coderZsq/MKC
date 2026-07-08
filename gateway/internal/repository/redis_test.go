package repository

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
)

func TestNewRedis(t *testing.T) {
	mr := miniredis.RunT(t)

	cfg := config.RedisConfig{
		Addr:     mr.Addr(),
		Password: "",
		DB:       0,
		PoolSize: 10,
	}

	client := NewRedis(cfg)
	require.NotNil(t, client)
	defer func() { _ = client.Close() }()

	assert.NoError(t, client.Ping(context.Background()).Err())
}
