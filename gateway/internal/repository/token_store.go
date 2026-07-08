package repository

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

// TokenStore persists refresh token sessions.
type TokenStore interface {
	Save(ctx context.Context, userUUID, tokenUUID string, session []byte, ttl time.Duration) error
	Get(ctx context.Context, userUUID, tokenUUID string) ([]byte, error)
	Delete(ctx context.Context, userUUID, tokenUUID string) error
	FindByTokenUUID(ctx context.Context, tokenUUID string) (userUUID string, session []byte, err error)
}

// RedisTokenStore stores refresh token sessions in Redis.
type RedisTokenStore struct {
	client *redis.Client
}

// NewRedisTokenStore creates a Redis-backed token store.
func NewRedisTokenStore(client *redis.Client) TokenStore {
	return &RedisTokenStore{client: client}
}

func (s *RedisTokenStore) refreshKey(userUUID, tokenUUID string) string {
	return fmt.Sprintf("refresh:%s:%s", userUUID, tokenUUID)
}

func (s *RedisTokenStore) Save(ctx context.Context, userUUID, tokenUUID string, session []byte, ttl time.Duration) error {
	key := s.refreshKey(userUUID, tokenUUID)
	if err := s.client.Set(ctx, key, session, ttl).Err(); err != nil {
		return fmt.Errorf("failed to save refresh session: %w", err)
	}
	return nil
}

func (s *RedisTokenStore) Get(ctx context.Context, userUUID, tokenUUID string) ([]byte, error) {
	key := s.refreshKey(userUUID, tokenUUID)
	val, err := s.client.Get(ctx, key).Bytes()
	if err != nil {
		if errors.Is(err, redis.Nil) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get refresh session: %w", err)
	}
	return val, nil
}

func (s *RedisTokenStore) Delete(ctx context.Context, userUUID, tokenUUID string) error {
	key := s.refreshKey(userUUID, tokenUUID)
	if err := s.client.Del(ctx, key).Err(); err != nil {
		return fmt.Errorf("failed to delete refresh session: %w", err)
	}
	return nil
}

func (s *RedisTokenStore) FindByTokenUUID(ctx context.Context, tokenUUID string) (string, []byte, error) {
	pattern := fmt.Sprintf("refresh:*:%s", tokenUUID)
	var cursor uint64
	for {
		keys, nextCursor, err := s.client.Scan(ctx, cursor, pattern, 100).Result()
		if err != nil {
			return "", nil, fmt.Errorf("failed to scan refresh sessions: %w", err)
		}
		for _, key := range keys {
			parts := strings.Split(key, ":")
			if len(parts) != 3 || parts[0] != "refresh" {
				continue
			}
			userUUID := parts[1]
			val, err := s.client.Get(ctx, key).Bytes()
			if err != nil {
				if errors.Is(err, redis.Nil) {
					continue
				}
				return "", nil, fmt.Errorf("failed to get refresh session: %w", err)
			}
			return userUUID, val, nil
		}
		cursor = nextCursor
		if cursor == 0 {
			break
		}
	}
	return "", nil, ErrNotFound
}
