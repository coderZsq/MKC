package repository

import (
	"context"
	"errors"
	"path/filepath"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func setupUnitOfWorkTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := gorm.Open(sqlite.Open(dbPath+"?_fk=1&_loc=auto"), &gorm.Config{})
	require.NoError(t, err)
	require.NoError(t, db.AutoMigrate(&model.User{}, &model.Conversation{}, &model.Message{}))
	return db
}

func TestUnitOfWork_Run_CommitsOnSuccess(t *testing.T) {
	db := setupUnitOfWorkTestDB(t)
	ctx := context.Background()
	user := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	uow := NewUnitOfWork(db)
	convRepo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "uow", []string{"res-1"})
	require.NoError(t, convRepo.Create(ctx, conv))

	err := uow.Run(ctx, func(_ ConversationRepository, msgRepo MessageRepository) error {
		return msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "hello"})
	})
	require.NoError(t, err)

	var count int64
	require.NoError(t, db.WithContext(ctx).Model(&model.Message{}).Count(&count).Error)
	assert.Equal(t, int64(1), count)
}

func TestUnitOfWork_Run_RollsBackOnError(t *testing.T) {
	db := setupUnitOfWorkTestDB(t)
	ctx := context.Background()
	user := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	uow := NewUnitOfWork(db)
	convRepo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "uow", []string{"res-1"})
	require.NoError(t, convRepo.Create(ctx, conv))

	err := uow.Run(ctx, func(_ ConversationRepository, msgRepo MessageRepository) error {
		require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "hello"}))
		return errors.New("forced rollback")
	})
	require.Error(t, err)

	var count int64
	require.NoError(t, db.WithContext(ctx).Model(&model.Message{}).Count(&count).Error)
	assert.Equal(t, int64(0), count)
}

func TestMessageRepository_ListByConversationID(t *testing.T) {
	db := setupUnitOfWorkTestDB(t)
	ctx := context.Background()
	user := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	convRepo := NewConversationRepository(db)
	conv := newTestConversation(user.ID, "msg", nil)
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := NewMessageRepository(db)
	for i := 0; i < 5; i++ {
		require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "msg"}))
	}

	messages, err := msgRepo.ListByConversationID(ctx, conv.ID, 3)
	require.NoError(t, err)
	assert.Len(t, messages, 3)

	messages, err = msgRepo.ListByConversationID(ctx, conv.ID, 0)
	require.NoError(t, err)
	assert.Len(t, messages, 5)
}

func TestConversationRepository_UpdateTitleByIDAndUserID_Forbidden(t *testing.T) {
	db := setupUnitOfWorkTestDB(t)
	ctx := context.Background()
	owner := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	other := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(owner).Error)
	require.NoError(t, db.WithContext(ctx).Create(other).Error)

	repo := NewConversationRepository(db)
	conv := newTestConversation(owner.ID, "title", nil)
	require.NoError(t, repo.Create(ctx, conv))

	err := repo.UpdateTitleByIDAndUserID(ctx, conv.ID, other.ID, "hacked")
	assert.ErrorIs(t, err, ErrForbidden)
}

func TestConversationRepository_TouchByIDAndUserID_Forbidden(t *testing.T) {
	db := setupUnitOfWorkTestDB(t)
	ctx := context.Background()
	owner := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	other := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(owner).Error)
	require.NoError(t, db.WithContext(ctx).Create(other).Error)

	repo := NewConversationRepository(db)
	conv := newTestConversation(owner.ID, "title", nil)
	require.NoError(t, repo.Create(ctx, conv))

	err := repo.TouchByIDAndUserID(ctx, conv.ID, other.ID)
	assert.ErrorIs(t, err, ErrForbidden)
}
