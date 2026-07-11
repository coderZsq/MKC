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
	user := newTestUser("convrepo@example.com", "hash", "Conv")
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
	assert.ErrorIs(t, err, ErrNotFound)

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

	require.NoError(t, repo.UpdateTitle(ctx, conv.ID, "new title"))
	require.NoError(t, repo.Touch(ctx, conv.ID))

	var updated model.Conversation
	require.NoError(t, db.WithContext(ctx).First(&updated, conv.ID).Error)
	assert.Equal(t, "new title", updated.Title)
	assert.False(t, updated.UpdatedAt.Before(updated.CreatedAt))
}

func TestMessageRepository_CreateAndList(t *testing.T) {
	db := setupConversationRepoTestDB(t)
	ctx := context.Background()
	user := newConversationRepoTestUser(t, db)
	convRepo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "", []string{"res-1"})
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := NewMessageRepository(db)
	userMsg := &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "hello"}
	require.NoError(t, msgRepo.Create(ctx, userMsg))
	assert.NotZero(t, userMsg.ID)

	citations := []map[string]any{{"resource_id": "res-1"}}
	citationsRaw, _ := json.Marshal(citations)
	assistantMsg := &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, ParentMessageID: &userMsg.ID, Role: "assistant", Content: "hi", Citations: citationsRaw}
	require.NoError(t, msgRepo.Create(ctx, assistantMsg))

	messages, err := msgRepo.ListByConversationID(ctx, conv.ID, 100)
	require.NoError(t, err)
	require.Len(t, messages, 2)
	assert.Equal(t, "hello", messages[0].Content)
	assert.Equal(t, "hi", messages[1].Content)
}
