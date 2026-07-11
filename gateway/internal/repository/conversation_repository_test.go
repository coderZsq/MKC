package repository

import (
	"context"
	"encoding/json"
	"path/filepath"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func setupConversationRepoTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := gorm.Open(sqlite.Open(dbPath+"?_fk=1&_loc=auto"), &gorm.Config{})
	require.NoError(t, err)
	require.NoError(t, db.AutoMigrate(&model.User{}, &model.Conversation{}, &model.Message{}))
	return db
}

func newTestConversation(ownerID uint64, title string, resourceIDs []string) *model.Conversation {
	raw, _ := json.Marshal(resourceIDs)
	return &model.Conversation{
		UUID:        uuid.NewString(),
		UserID:      ownerID,
		Title:       title,
		ResourceIDs: raw,
	}
}

func newConversationRepoTestUser(t *testing.T, db *gorm.DB) *model.User {
	ctx := context.Background()
	user := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash", Nickname: "Conv"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	return user
}

func TestConversationRepository_CreateAndGet(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user := newConversationRepoTestUser(t, db)

	repo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "title", []string{"res-1"})
	require.NoError(t, repo.Create(ctx, conv))
	assert.NotZero(t, conv.ID)

	found, err := repo.GetByUUIDAndUserID(ctx, conv.UUID, user.ID)
	require.NoError(t, err)
	assert.Equal(t, conv.UUID, found.UUID)

	_, err = repo.GetByUUIDAndUserID(ctx, conv.UUID, user.ID+1)
	assert.ErrorIs(t, err, ErrForbidden)

	_, err = repo.GetByUUIDAndUserID(ctx, uuid.NewString(), user.ID)
	assert.ErrorIs(t, err, ErrNotFound)
}

func TestConversationRepository_UpdateTitleAndTouch(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user := newConversationRepoTestUser(t, db)

	repo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "", []string{"res-1"})
	require.NoError(t, repo.Create(ctx, conv))

	require.NoError(t, repo.UpdateTitleByIDAndUserID(ctx, conv.ID, user.ID, "new title"))
	require.NoError(t, repo.TouchByIDAndUserID(ctx, conv.ID, user.ID))

	var updated model.Conversation
	require.NoError(t, db.WithContext(ctx).First(&updated, conv.ID).Error)
	assert.Equal(t, "new title", updated.Title)
	assert.False(t, updated.UpdatedAt.Before(updated.CreatedAt))
}

func TestConversationRepository_ScopedMethods_NotFound(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user := newConversationRepoTestUser(t, db)

	repo := NewConversationRepository(db)

	assert.ErrorIs(t, repo.UpdateTitleByIDAndUserID(ctx, 999999, user.ID, "x"), ErrNotFound)
	assert.ErrorIs(t, repo.TouchByIDAndUserID(ctx, 999999, user.ID), ErrNotFound)
	assert.ErrorIs(t, repo.DeleteByUUIDAndUserID(ctx, uuid.NewString(), user.ID), ErrNotFound)
}

func TestConversationRepository_ListByUserID(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user1 := newConversationRepoTestUser(t, db)
	user2 := newConversationRepoTestUser(t, db)

	repo := NewConversationRepository(db)
	require.NoError(t, repo.Create(ctx, newTestConversation(user1.ID, "a", nil)))
	require.NoError(t, repo.Create(ctx, newTestConversation(user1.ID, "b", nil)))
	require.NoError(t, repo.Create(ctx, newTestConversation(user2.ID, "c", nil)))

	conversations, total, err := repo.ListByUserID(ctx, user1.ID, 1, 10)
	require.NoError(t, err)
	assert.Equal(t, int64(2), total)
	assert.Len(t, conversations, 2)
	assert.Equal(t, "b", conversations[0].Title)
	assert.Equal(t, "a", conversations[1].Title)
}

func TestConversationRepository_GetByUUIDAndUserID(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user := newConversationRepoTestUser(t, db)
	repo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "title", nil)
	require.NoError(t, repo.Create(ctx, conv))

	found, err := repo.GetByUUIDAndUserID(ctx, conv.UUID, user.ID)
	require.NoError(t, err)
	assert.Equal(t, conv.UUID, found.UUID)

	_, err = repo.GetByUUIDAndUserID(ctx, conv.UUID, user.ID+1)
	assert.ErrorIs(t, err, ErrForbidden)

	_, err = repo.GetByUUIDAndUserID(ctx, uuid.NewString(), user.ID)
	assert.ErrorIs(t, err, ErrNotFound)
}

func TestConversationRepository_DeleteByUUIDAndUserID(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user := newConversationRepoTestUser(t, db)
	repo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "title", nil)
	require.NoError(t, repo.Create(ctx, conv))

	msgRepo := NewMessageRepository(db)
	require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "hello"}))

	require.NoError(t, repo.DeleteByUUIDAndUserID(ctx, conv.UUID, user.ID))

	_, err := repo.GetByUUIDAndUserID(ctx, conv.UUID, user.ID)
	assert.ErrorIs(t, err, ErrNotFound)

	var count int64
	require.NoError(t, db.WithContext(ctx).Model(&model.Message{}).Where("conversation_id = ?", conv.ID).Count(&count).Error)
	assert.Equal(t, int64(0), count)
}

func TestConversationRepository_DeleteByUUIDAndUserID_Forbidden(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	owner := newConversationRepoTestUser(t, db)
	other := newConversationRepoTestUser(t, db)
	repo := NewConversationRepository(db)
	conv := newTestConversation(owner.ID, "title", nil)
	require.NoError(t, repo.Create(ctx, conv))

	err := repo.DeleteByUUIDAndUserID(ctx, conv.UUID, other.ID)
	assert.ErrorIs(t, err, ErrForbidden)

	got, err := repo.GetByUUIDAndUserID(ctx, conv.UUID, owner.ID)
	require.NoError(t, err)
	assert.Equal(t, conv.UUID, got.UUID)
}

func TestMessageRepository_ListByConversationIDPaginated(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user := newConversationRepoTestUser(t, db)
	convRepo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "", nil)
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := NewMessageRepository(db)
	for i := 0; i < 25; i++ {
		msg := &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "msg"}
		require.NoError(t, msgRepo.Create(ctx, msg))
	}

	messages, total, err := msgRepo.ListByConversationIDPaginated(ctx, conv.ID, 1, 20)
	require.NoError(t, err)
	assert.Equal(t, int64(25), total)
	assert.Len(t, messages, 20)

	messages, total, err = msgRepo.ListByConversationIDPaginated(ctx, conv.ID, 2, 20)
	require.NoError(t, err)
	assert.Len(t, messages, 5)
	assert.Equal(t, int64(25), total)

	// page=0/limit=0 fall back to defaults (page=1, limit=20)
	messages, total, err = msgRepo.ListByConversationIDPaginated(ctx, conv.ID, 0, 0)
	require.NoError(t, err)
	assert.Equal(t, int64(25), total)
	assert.Len(t, messages, 20)
}
