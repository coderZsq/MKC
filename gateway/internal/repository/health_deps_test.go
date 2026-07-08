package repository

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
)

func TestMySQLDependency_Ping(t *testing.T) {
	db := setupResourceTestDB(t)
	dep := &MySQLDependency{DB: db}

	assert.Equal(t, "mysql", dep.Name())
	assert.NoError(t, dep.Ping(context.Background()))
}

func TestMySQLDependency_Ping_NilDB(t *testing.T) {
	dep := &MySQLDependency{DB: nil}

	assert.ErrorIs(t, dep.Ping(context.Background()), gorm.ErrInvalidDB)
}

func TestRedisDependency_Ping(t *testing.T) {
	mr := miniredis.RunT(t)
	client := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = client.Close() })

	dep := &RedisDependency{Client: client}

	assert.Equal(t, "redis", dep.Name())
	require.NoError(t, dep.Ping(context.Background()))
}

func TestRedisDependency_Ping_NilClient(t *testing.T) {
	dep := &RedisDependency{Client: nil}

	assert.ErrorIs(t, dep.Ping(context.Background()), redis.Nil)
}
