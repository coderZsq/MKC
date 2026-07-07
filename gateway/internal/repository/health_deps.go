package repository

import (
	"context"

	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"
)

// MySQLDependency wraps a GORM DB as a health-check dependency.
type MySQLDependency struct {
	DB *gorm.DB
}

// Name returns the dependency name.
func (d *MySQLDependency) Name() string { return "mysql" }

// Ping executes a lightweight query to verify connectivity.
func (d *MySQLDependency) Ping(_ context.Context) error {
	if d.DB == nil {
		return gorm.ErrInvalidDB
	}
	return d.DB.Exec("SELECT 1").Error
}

// RedisDependency wraps a Redis client as a health-check dependency.
type RedisDependency struct {
	Client *redis.Client
}

// Name returns the dependency name.
func (d *RedisDependency) Name() string { return "redis" }

// Ping sends a PING command to Redis.
func (d *RedisDependency) Ping(ctx context.Context) error {
	if d.Client == nil {
		return redis.Nil
	}
	return d.Client.Ping(ctx).Err()
}
