package service

import (
	"context"
	"encoding/json"
	"errors"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"go.uber.org/zap"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func setupConversationServiceTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := gorm.Open(sqlite.Open(dbPath+"?_fk=1&_loc=auto"), &gorm.Config{})
	require.NoError(t, err)
	require.NoError(t, db.AutoMigrate(&model.User{}, &model.Conversation{}, &model.Message{}, &model.Resource{}))
	return db
}

func newConversationServiceTestUser(t *testing.T, db *gorm.DB) *model.User {
	ctx := context.Background()
	user := &model.User{UUID: uuid.NewString(), Email: uuid.NewString() + "@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	return user
}

func TestConversationService_Create(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	svc := NewConversationService(repository.NewConversationRepository(db), repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "default", zap.NewNop())
	conv, err := svc.Create(ctx, user.ID, CreateConversationRequest{Title: "project", ResourceIDs: []string{"res-1"}})
	require.NoError(t, err)
	assert.Equal(t, "project", conv.Title)
	assert.Equal(t, []string{"res-1"}, conv.ResourceIDs)
	assert.NotEmpty(t, conv.ID)
}

func TestConversationService_Create_DefaultTitle(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	svc := NewConversationService(repository.NewConversationRepository(db), repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "默认", zap.NewNop())
	conv, err := svc.Create(ctx, user.ID, CreateConversationRequest{})
	require.NoError(t, err)
	assert.Equal(t, "默认", conv.Title)
}

func TestConversationService_Create_AcceptsOwnedResourceIDs(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	for _, id := range []string{"res-1", "res-2"} {
		require.NoError(t, db.WithContext(ctx).Create(&model.Resource{
			UUID: id, UserID: user.ID, Name: "doc", Type: "document_parse",
			Status: 1, StorageKey: "k", SizeBytes: 1, MimeType: "text/plain",
		}).Error)
	}

	svc := NewConversationService(repository.NewConversationRepository(db), repository.NewMessageRepository(db), repository.NewResourceRepository(db), repository.NewUnitOfWork(db), "default", zap.NewNop())
	conv, err := svc.Create(ctx, user.ID, CreateConversationRequest{Title: "project", ResourceIDs: []string{"res-1", "res-2"}})
	require.NoError(t, err)
	assert.Equal(t, []string{"res-1", "res-2"}, conv.ResourceIDs)
}

func TestConversationService_Create_RejectsForeignResourceIDs(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)
	other := newConversationServiceTestUser(t, db)

	require.NoError(t, db.WithContext(ctx).Create(&model.Resource{
		UUID: "res-other", UserID: other.ID, Name: "doc", Type: "document_parse",
		Status: 1, StorageKey: "k", SizeBytes: 1, MimeType: "text/plain",
	}).Error)

	svc := NewConversationService(repository.NewConversationRepository(db), repository.NewMessageRepository(db), repository.NewResourceRepository(db), repository.NewUnitOfWork(db), "default", zap.NewNop())
	_, err := svc.Create(ctx, user.ID, CreateConversationRequest{Title: "project", ResourceIDs: []string{"res-other"}})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "BAD_REQUEST")
}

func TestNewConversationService_NilLoggerAndDefaultTitle(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	// nil logger + empty defaultTitle fall back to safe defaults without panicking
	svc := NewConversationService(repository.NewConversationRepository(db), repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "", nil)
	conv, err := svc.Create(ctx, user.ID, CreateConversationRequest{})
	require.NoError(t, err)
	assert.Equal(t, "新会话", conv.Title)
}

func TestValidateCreateConversationRequest(t *testing.T) {
	ctx := context.Background()
	errRepo := &stubResourceRepository{countByUUIDsAndUserFunc: func(context.Context, []string, uint64) (int64, error) {
		return 0, errors.New("db down")
	}}
	mismatchRepo := &stubResourceRepository{countByUUIDsAndUserFunc: func(context.Context, []string, uint64) (int64, error) {
		return 0, nil
	}}

	tests := []struct {
		name string
		req  CreateConversationRequest
		repo repository.ResourceRepository
	}{
		{"title too long", CreateConversationRequest{Title: strings.Repeat("a", maxTitleLength+1)}, nil},
		{"too many resource_ids", CreateConversationRequest{ResourceIDs: make([]string, maxResourceIDs+1)}, nil},
		{"resource repo error", CreateConversationRequest{ResourceIDs: []string{"r1"}}, errRepo},
		{"resource count mismatch", CreateConversationRequest{ResourceIDs: []string{"r1"}}, mismatchRepo},
		{"invalid model_config", CreateConversationRequest{ModelConfig: map[string]any{"x": make(chan int)}}, nil},
		{"model_config too large", CreateConversationRequest{ModelConfig: map[string]any{"x": strings.Repeat("a", maxModelConfigBytes+1)}}, nil},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := validateCreateConversationRequest(ctx, tc.req, 1, tc.repo)
			require.Error(t, err)
		})
	}

	// valid request returns nil
	okRepo := &stubResourceRepository{countByUUIDsAndUserFunc: func(context.Context, []string, uint64) (int64, error) {
		return 1, nil
	}}
	require.NoError(t, validateCreateConversationRequest(ctx, CreateConversationRequest{Title: "ok", ResourceIDs: []string{"r1"}, ModelConfig: map[string]any{"k": "v"}}, 1, okRepo))
}

func TestConversationService_ListAndOwnership(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user1 := newConversationServiceTestUser(t, db)
	user2 := newConversationServiceTestUser(t, db)

	repo := repository.NewConversationRepository(db)
	require.NoError(t, repo.Create(ctx, &model.Conversation{UUID: uuid.NewString(), UserID: user1.ID, Title: "a"}))
	time.Sleep(10 * time.Millisecond)
	require.NoError(t, repo.Create(ctx, &model.Conversation{UUID: uuid.NewString(), UserID: user1.ID, Title: "b"}))
	require.NoError(t, repo.Create(ctx, &model.Conversation{UUID: uuid.NewString(), UserID: user2.ID, Title: "c"}))

	svc := NewConversationService(repo, repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "", zap.NewNop())
	conversations, total, err := svc.List(ctx, user1.ID, 1, 10)
	require.NoError(t, err)
	assert.Equal(t, int64(2), total)
	assert.Len(t, conversations, 2)
	assert.Equal(t, "b", conversations[0].Title)
}

func TestConversationService_Get_Ownership(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user1 := newConversationServiceTestUser(t, db)
	user2 := newConversationServiceTestUser(t, db)

	repo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user1.ID, Title: "mine"}
	require.NoError(t, repo.Create(ctx, conv))

	svc := NewConversationService(repo, repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "", zap.NewNop())
	found, err := svc.Get(ctx, user1.ID, conv.UUID)
	require.NoError(t, err)
	assert.Equal(t, "mine", found.Title)

	_, err = svc.Get(ctx, user2.ID, conv.UUID)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "FORBIDDEN")
}

func TestConversationService_Delete(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	repo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: "delete"}
	require.NoError(t, repo.Create(ctx, conv))

	svc := NewConversationService(repo, repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "", zap.NewNop())
	require.NoError(t, svc.Delete(ctx, user.ID, conv.UUID))

	_, err := svc.Get(ctx, user.ID, conv.UUID)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "CONVERSATION_NOT_FOUND")
}

func TestConversationService_ListMessages(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	convRepo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: "messages"}
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := repository.NewMessageRepository(db)
	for i := 0; i < 5; i++ {
		require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "msg"}))
	}

	svc := NewConversationService(convRepo, msgRepo, nil, repository.NewUnitOfWork(db), "", zap.NewNop())
	res, err := svc.ListMessages(ctx, user.ID, conv.UUID, 1, 3)
	require.NoError(t, err)
	assert.Equal(t, int64(5), res.Total)
	assert.Len(t, res.Items, 3)

	_, err = svc.ListMessages(ctx, 999, conv.UUID, 1, 3)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "FORBIDDEN")
}

func TestConversationService_ListMessages_IncludesReasoning(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	convRepo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: "messages"}
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := repository.NewMessageRepository(db)
	require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "assistant", Content: "answer", Reasoning: "hidden thought"}))

	svc := NewConversationService(convRepo, msgRepo, nil, repository.NewUnitOfWork(db), "", zap.NewNop())
	res, err := svc.ListMessages(ctx, user.ID, conv.UUID, 1, 10)
	require.NoError(t, err)
	require.Len(t, res.Items, 1)
	assert.Equal(t, "answer", res.Items[0].Content)
	assert.Equal(t, "hidden thought", res.Items[0].Reasoning)
}

func TestConversationService_CreateMessage(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	convRepo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: "messages"}
	require.NoError(t, convRepo.Create(ctx, conv))

	svc := NewConversationService(convRepo, repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "", zap.NewNop())
	msg, err := svc.CreateMessage(ctx, user.ID, conv.UUID, CreateMessageRequest{Role: "user", Content: "hello", Model: "glm-4"})
	require.NoError(t, err)
	assert.Equal(t, "user", msg.Role)
	assert.Equal(t, "glm-4", msg.Model)

	_, err = svc.CreateMessage(ctx, user.ID, conv.UUID, CreateMessageRequest{Role: "bot", Content: "x"})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "BAD_REQUEST")
}

func TestConversationService_CreateMessage_NotFound(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	svc := NewConversationService(repository.NewConversationRepository(db), repository.NewMessageRepository(db), nil, repository.NewUnitOfWork(db), "", zap.NewNop())
	_, err := svc.CreateMessage(ctx, user.ID, uuid.NewString(), CreateMessageRequest{Role: "user", Content: "hello"})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "CONVERSATION_NOT_FOUND")
}

func TestContextWindowService_BuildMessages(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	convRepo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: "ctx"}
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := repository.NewMessageRepository(db)
	for i := 0; i < 30; i++ {
		role := "user"
		if i%2 == 1 {
			role = "assistant"
		}
		require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: role, Content: "short"}))
	}

	svc := NewContextWindowService(msgRepo, 10, 1000)
	history, err := svc.BuildMessages(ctx, conv.ID, "question")
	require.NoError(t, err)
	assert.Len(t, history, 10)
	assert.Equal(t, "user", history[0].Role)
	assert.Equal(t, "user", history[len(history)-2].Role)
	assert.Equal(t, "assistant", history[len(history)-1].Role)
}

func TestContextWindowService_BuildMessages_PreservesMetadata(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	convRepo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: "ctx"}
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := repository.NewMessageRepository(db)
	citations := json.RawMessage(`[{"resource_id":"res-1","page":6}]`)
	require.NoError(t, msgRepo.Create(ctx, &model.Message{
		UUID:           uuid.NewString(),
		ConversationID: conv.ID,
		Role:           "assistant",
		Content:        "answer",
		Reasoning:      "thinking",
		Citations:      citations,
	}))

	svc := NewContextWindowService(msgRepo, 10, 1000)
	history, err := svc.BuildMessages(ctx, conv.ID, "question")
	require.NoError(t, err)
	require.Len(t, history, 1)
	assert.Equal(t, "thinking", history[0].Reasoning)
	assert.JSONEq(t, string(citations), string(history[0].Citations))
}

func TestContextWindowService_Truncation(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := newConversationServiceTestUser(t, db)

	convRepo := repository.NewConversationRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: "ctx"}
	require.NoError(t, convRepo.Create(ctx, conv))

	msgRepo := repository.NewMessageRepository(db)
	require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "old"}))
	require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "assistant", Content: "old-answer"}))
	require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "new"}))
	require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "assistant", Content: "new-answer"}))

	svc := NewContextWindowService(msgRepo, 100, 10)
	history, err := svc.BuildMessages(ctx, conv.ID, "q")
	require.NoError(t, err)
	assert.Len(t, history, 2)
	assert.Equal(t, "new", history[0].Content)
	assert.Equal(t, "new-answer", history[1].Content)
}

func TestQAService_Ask_UsesContextWindow(t *testing.T) {
	db := setupConversationServiceTestDB(t)
	ctx := context.Background()
	user := &model.User{UUID: uuid.NewString(), Email: "qa@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	convRepo := repository.NewConversationRepository(db)
	msgRepo := repository.NewMessageRepository(db)
	conv := &model.Conversation{UUID: uuid.NewString(), UserID: user.ID, Title: ""}
	require.NoError(t, convRepo.Create(ctx, conv))

	for i := 0; i < 3; i++ {
		require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "q"}))
		require.NoError(t, msgRepo.Create(ctx, &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "assistant", Content: "a"}))
	}

	aiclient := &mockAIClient{
		events: []SSEEvent{
			{Event: "done", Data: []byte(`{"finish_reason":"stop"}`), Raw: "event: done\ndata: {}\n\n"},
		},
	}
	ctxWindow := NewContextWindowService(msgRepo, 2, 1000)
	svc := NewQAService(aiclient, convRepo, msgRepo, nil, WithContextWindowService(ctxWindow))

	_, err := svc.Ask(ctx, user.ID, user.UUID, conv.UUID, "new question")
	require.NoError(t, err)

	require.Len(t, aiclient.lastRequest.History, 2)
}
