package repository

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func setupUserTestDB(t *testing.T) *gorm.DB {
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := gorm.Open(sqlite.Open(dbPath+"?_loc=auto"), &gorm.Config{})
	require.NoError(t, err)

	err = db.AutoMigrate(&model.User{})
	require.NoError(t, err)

	return db
}

func newTestUser(email, passwordHash, nickname string) *model.User {
	return &model.User{
		UUID:         uuid.NewString(),
		Email:        email,
		PasswordHash: passwordHash,
		Nickname:     nickname,
		Status:       1,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}
}

func TestUserRepository_CreateAndGet(t *testing.T) {
	db := setupUserTestDB(t)
	repo := NewUserRepository(db)
	ctx := context.Background()

	user := newTestUser("alice@example.com", "hashed", "Alice")
	err := repo.Create(ctx, user)
	require.NoError(t, err)
	assert.NotZero(t, user.ID)

	byEmail, err := repo.GetByEmail(ctx, "alice@example.com")
	require.NoError(t, err)
	assert.Equal(t, user.UUID, byEmail.UUID)
	assert.Equal(t, "alice@example.com", byEmail.Email)
	assert.Equal(t, "Alice", byEmail.Nickname)

	byUUID, err := repo.GetByUUID(ctx, user.UUID)
	require.NoError(t, err)
	assert.Equal(t, user.Email, byUUID.Email)
}

func TestUserRepository_Create_DuplicateEmail(t *testing.T) {
	db := setupUserTestDB(t)
	repo := NewUserRepository(db)
	ctx := context.Background()

	user1 := newTestUser("dupe@example.com", "hashed1", "User1")
	user2 := newTestUser("dupe@example.com", "hashed2", "User2")

	require.NoError(t, repo.Create(ctx, user1))
	err := repo.Create(ctx, user2)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "CONFLICT")
	assert.Contains(t, err.Error(), "email already exists")
}

func TestUserRepository_GetByEmail_NotFound(t *testing.T) {
	db := setupUserTestDB(t)
	repo := NewUserRepository(db)
	ctx := context.Background()

	_, err := repo.GetByEmail(ctx, "missing@example.com")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "NOT_FOUND")
}

func TestUserRepository_GetByUUID_NotFound(t *testing.T) {
	db := setupUserTestDB(t)
	repo := NewUserRepository(db)
	ctx := context.Background()

	_, err := repo.GetByUUID(ctx, uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "NOT_FOUND")
}
