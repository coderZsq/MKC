package service

import (
	"context"
	"encoding/json"
	"path/filepath"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func setupConversationTestDB(t *testing.T) *gorm.DB {
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

type mockAIClient struct {
	events      []SSEEvent
	err         error
	lastRequest QARequest
}

func (m *mockAIClient) StreamQA(ctx context.Context, req QARequest) (<-chan SSEEvent, error) {
	m.lastRequest = req
	if m.err != nil {
		return nil, m.err
	}
	ch := make(chan SSEEvent, len(m.events))
	for _, ev := range m.events {
		ch <- ev
	}
	close(ch)
	return ch, nil
}

func TestQAService_Ask_Success(t *testing.T) {
	db := setupConversationTestDB(t)
	ctx := context.Background()

	user := &model.User{UUID: uuid.NewString(), Email: "qa@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	conv := newTestConversation(user.ID, "", []string{"res-1"})
	require.NoError(t, db.WithContext(ctx).Create(conv).Error)

	aiclient := &mockAIClient{
		events: []SSEEvent{
			{Event: "chunk", Data: []byte(`{"delta":"hello"}`), Raw: "event: chunk\ndata: {\"delta\":\"hello\"}\n\n"},
			{Event: "chunk", Data: []byte(`{"delta":" world"}`), Raw: "event: chunk\ndata: {\"delta\":\" world\"}\n\n"},
			{Event: "done", Data: []byte(`{"finish_reason":"stop"}`), Raw: "event: done\ndata: {\"finish_reason\":\"stop\"}\n\n"},
		},
	}

	convRepo := repository.NewConversationRepository(db)
	msgRepo := repository.NewMessageRepository(db)
	svc := NewQAService(aiclient, convRepo, msgRepo, nil)

	events, err := svc.Ask(ctx, user.ID, user.UUID, conv.UUID, "hi")
	require.NoError(t, err)

	var collected []SSEEvent
	for ev := range events {
		collected = append(collected, ev)
	}
	require.Len(t, collected, 3)

	var messages []model.Message
	require.NoError(t, db.WithContext(ctx).Where("conversation_id = ?", conv.ID).Order("id asc").Find(&messages).Error)
	require.Len(t, messages, 2)
	assert.Equal(t, "user", messages[0].Role)
	assert.Equal(t, "hi", messages[0].Content)
	assert.Equal(t, "assistant", messages[1].Role)
	assert.Equal(t, "hello world", messages[1].Content)
	assert.NotNil(t, messages[1].ParentMessageID)
	assert.Equal(t, messages[0].ID, *messages[1].ParentMessageID)
}

func TestQAService_Ask_ConversationNotFound(t *testing.T) {
	db := setupConversationTestDB(t)
	ctx := context.Background()

	user := &model.User{UUID: uuid.NewString(), Email: "qa@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	svc := NewQAService(
		&mockAIClient{},
		repository.NewConversationRepository(db),
		repository.NewMessageRepository(db),
		nil,
	)

	_, err := svc.Ask(ctx, user.ID, user.UUID, uuid.NewString(), "hi")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "CONVERSATION_NOT_FOUND")
}

func TestQAService_Ask_InvalidQuestion(t *testing.T) {
	db := setupConversationTestDB(t)
	ctx := context.Background()
	user := &model.User{UUID: uuid.NewString(), Email: "qa@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	conv := newTestConversation(user.ID, "", []string{"res-1"})
	require.NoError(t, db.WithContext(ctx).Create(conv).Error)

	svc := NewQAService(
		&mockAIClient{},
		repository.NewConversationRepository(db),
		repository.NewMessageRepository(db),
		nil,
	)

	_, err := svc.Ask(ctx, user.ID, user.UUID, conv.UUID, "")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "question")
}

func TestQAService_Ask_ErrorEventSavesPartialAnswer(t *testing.T) {
	db := setupConversationTestDB(t)
	ctx := context.Background()

	user := &model.User{UUID: uuid.NewString(), Email: "qa@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	conv := newTestConversation(user.ID, "", []string{"res-1"})
	require.NoError(t, db.WithContext(ctx).Create(conv).Error)

	aiclient := &mockAIClient{
		events: []SSEEvent{
			{Event: "chunk", Data: []byte(`{"delta":"partial"}`), Raw: "event: chunk\ndata: {\"delta\":\"partial\"}\n\n"},
			{Event: "error", Data: []byte(`{"error_code":"LLM_TIMEOUT"}`), Raw: "event: error\ndata: {\"error_code\":\"LLM_TIMEOUT\"}\n\n"},
		},
	}

	svc := NewQAService(aiclient, repository.NewConversationRepository(db), repository.NewMessageRepository(db), nil)

	events, err := svc.Ask(ctx, user.ID, user.UUID, conv.UUID, "q")
	require.NoError(t, err)
	for range events {
	}

	var messages []model.Message
	require.NoError(t, db.WithContext(ctx).Where("conversation_id = ? AND role = ?", conv.ID, "assistant").Find(&messages).Error)
	require.Len(t, messages, 1)
	assert.Equal(t, "partial", messages[0].Content)
}

func TestQAService_Ask_IncludesHistory(t *testing.T) {
	db := setupConversationTestDB(t)
	ctx := context.Background()

	user := &model.User{UUID: uuid.NewString(), Email: "qa@example.com", PasswordHash: "hash"}
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	conv := newTestConversation(user.ID, "", []string{"res-1"})
	require.NoError(t, db.WithContext(ctx).Create(conv).Error)

	prevUser := &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "user", Content: "previous"}
	prevAssistant := &model.Message{UUID: uuid.NewString(), ConversationID: conv.ID, Role: "assistant", Content: "answer"}
	require.NoError(t, db.WithContext(ctx).Create(prevUser).Error)
	require.NoError(t, db.WithContext(ctx).Create(prevAssistant).Error)

	var captured QARequest
	aiclient := &mockAIClient{
		events: []SSEEvent{
			{Event: "done", Data: []byte(`{"finish_reason":"stop"}`), Raw: "event: done\ndata: {}\n\n"},
		},
	}

	svc := NewQAService(aiclient, repository.NewConversationRepository(db), repository.NewMessageRepository(db), nil)
	_, err := svc.Ask(ctx, user.ID, user.UUID, conv.UUID, "new")
	require.NoError(t, err)

	captured = aiclient.lastRequest
	require.Len(t, captured.History, 2)
	assert.Equal(t, "user", captured.History[0].Role)
	assert.Equal(t, "previous", captured.History[0].Content)
	assert.Equal(t, "assistant", captured.History[1].Role)
	assert.Equal(t, "answer", captured.History[1].Content)
	assert.Equal(t, "new", captured.Question)
}
