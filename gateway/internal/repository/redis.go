package repository

import (
	"github.com/redis/go-redis/v9"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
)

// NewRedis creates a Redis client from config.
func NewRedis(cfg config.RedisConfig) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     cfg.Addr,
		Password: cfg.Password,
		DB:       cfg.DB,
		PoolSize: cfg.PoolSize,
	})
}
