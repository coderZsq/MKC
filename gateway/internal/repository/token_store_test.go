package repository

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupRedisTokenStore(t *testing.T) (*miniredis.Miniredis, TokenStore) {
	mr := miniredis.RunT(t)
	client := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = client.Close() })
	return mr, NewRedisTokenStore(client)
}

func TestRedisTokenStore_SaveAndGet(t *testing.T) {
	_, store := setupRedisTokenStore(t)
	ctx := context.Background()

	userUUID := uuid.NewString()
	tokenUUID := uuid.NewString()
	session := []byte(`{"user_uuid":"` + userUUID + `","email":"a@b.com"}`)

	require.NoError(t, store.Save(ctx, userUUID, tokenUUID, session, time.Hour))

	got, err := store.Get(ctx, userUUID, tokenUUID)
	require.NoError(t, err)
	assert.Equal(t, session, got)
}

func TestRedisTokenStore_Get_NotFound(t *testing.T) {
	_, store := setupRedisTokenStore(t)
	ctx := context.Background()

	_, err := store.Get(ctx, uuid.NewString(), uuid.NewString())
	assert.Error(t, err)
}

func TestRedisTokenStore_Delete(t *testing.T) {
	_, store := setupRedisTokenStore(t)
	ctx := context.Background()

	userUUID := uuid.NewString()
	tokenUUID := uuid.NewString()
	session := []byte(`{"user_uuid":"` + userUUID + `"}`)

	require.NoError(t, store.Save(ctx, userUUID, tokenUUID, session, time.Hour))
	require.NoError(t, store.Delete(ctx, userUUID, tokenUUID))

	_, err := store.Get(ctx, userUUID, tokenUUID)
	assert.Error(t, err)
}

func TestRedisTokenStore_FindByTokenUUID(t *testing.T) {
	_, store := setupRedisTokenStore(t)
	ctx := context.Background()

	userUUID := uuid.NewString()
	tokenUUID := uuid.NewString()
	session := []byte(`{"user_uuid":"` + userUUID + `"}`)

	require.NoError(t, store.Save(ctx, userUUID, tokenUUID, session, time.Hour))

	foundUserUUID, foundSession, err := store.FindByTokenUUID(ctx, tokenUUID)
	require.NoError(t, err)
	assert.Equal(t, userUUID, foundUserUUID)
	assert.Equal(t, session, foundSession)
}

func TestRedisTokenStore_FindByTokenUUID_NotFound(t *testing.T) {
	_, store := setupRedisTokenStore(t)
	ctx := context.Background()

	_, _, err := store.FindByTokenUUID(ctx, uuid.NewString())
	assert.Error(t, err)
}
