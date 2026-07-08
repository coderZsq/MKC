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

func setupResourceTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := gorm.Open(sqlite.Open(dbPath+"?_fk=1&_loc=auto"), &gorm.Config{})
	require.NoError(t, err)

	require.NoError(t, db.AutoMigrate(&model.User{}, &model.Resource{}, &model.Task{}))

	return db
}

func newTestResource(userID uint64, name, mime string) *model.Resource {
	return &model.Resource{
		UUID:       uuid.NewString(),
		UserID:     userID,
		Name:       name,
		Type:       "document_parse",
		Status:     1,
		StorageKey: "users/uuid/resources/key",
		SizeBytes:  42,
		MimeType:   mime,
		CreatedAt:  time.Now(),
		UpdatedAt:  time.Now(),
	}
}

func TestResourceRepository_CreateAndUpdateStatus(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewResourceRepository(db)
	ctx := context.Background()

	user := newTestUser("resourceowner@example.com", "hashed", "Owner")
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	resource := newTestResource(user.ID, "doc.txt", "text/plain")
	err := repo.Create(ctx, resource)
	require.NoError(t, err)
	assert.NotZero(t, resource.ID)

	err = repo.UpdateStatus(ctx, resource.ID, 2)
	require.NoError(t, err)

	var updated struct{ Status uint8 }
	require.NoError(t, db.WithContext(ctx).Model(&model.Resource{}).Select("status").First(&updated, resource.ID).Error)
	assert.Equal(t, uint8(2), updated.Status)
}

func TestResourceRepository_Create_DuplicateUUID(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewResourceRepository(db)
	ctx := context.Background()

	user1 := newTestUser("res1@example.com", "hashed1", "Owner1")
	user2 := newTestUser("res2@example.com", "hashed2", "Owner2")
	require.NoError(t, db.WithContext(ctx).Create(user1).Error)
	require.NoError(t, db.WithContext(ctx).Create(user2).Error)

	resource := newTestResource(user1.ID, "doc.txt", "text/plain")
	require.NoError(t, repo.Create(ctx, resource))

	duplicate := newTestResource(user2.ID, "other.txt", "text/plain")
	duplicate.UUID = resource.UUID
	err := repo.Create(ctx, duplicate)
	require.Error(t, err)
}

func TestResourceRepository_GetByUUIDAndUserID(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewResourceRepository(db)
	ctx := context.Background()

	user1 := newTestUser("resowner1@example.com", "hashed1", "Owner1")
	user2 := newTestUser("resowner2@example.com", "hashed2", "Owner2")
	require.NoError(t, db.WithContext(ctx).Create(user1).Error)
	require.NoError(t, db.WithContext(ctx).Create(user2).Error)

	resource := newTestResource(user1.ID, "doc.txt", "text/plain")
	require.NoError(t, repo.Create(ctx, resource))

	found, err := repo.GetByUUIDAndUserID(ctx, resource.UUID, user1.ID)
	require.NoError(t, err)
	assert.Equal(t, resource.UUID, found.UUID)

	_, err = repo.GetByUUIDAndUserID(ctx, resource.UUID, user2.ID)
	assert.ErrorIs(t, err, ErrNotFound)

	_, err = repo.GetByUUIDAndUserID(ctx, uuid.NewString(), user1.ID)
	assert.ErrorIs(t, err, ErrNotFound)
}
