package repository

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

func closedRedisTokenStore(t *testing.T) TokenStore {
	t.Helper()
	mr := miniredis.RunT(t)
	addr := mr.Addr()
	mr.Close()
	client := redis.NewClient(&redis.Options{Addr: addr})
	t.Cleanup(func() { _ = client.Close() })
	return NewRedisTokenStore(client)
}

func TestRedisTokenStore_Save_Error(t *testing.T) {
	store := closedRedisTokenStore(t)

	err := store.Save(context.Background(), uuid.NewString(), uuid.NewString(), []byte("x"), 0)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to save refresh session")
}

func TestRedisTokenStore_Get_Error(t *testing.T) {
	store := closedRedisTokenStore(t)

	_, err := store.Get(context.Background(), uuid.NewString(), uuid.NewString())
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to get refresh session")
}

func TestRedisTokenStore_Delete_Error(t *testing.T) {
	store := closedRedisTokenStore(t)

	err := store.Delete(context.Background(), uuid.NewString(), uuid.NewString())
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to delete refresh session")
}

func TestRedisTokenStore_FindByTokenUUID_ScanError(t *testing.T) {
	store := closedRedisTokenStore(t)

	_, _, err := store.FindByTokenUUID(context.Background(), uuid.NewString())
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to scan refresh sessions")
}

