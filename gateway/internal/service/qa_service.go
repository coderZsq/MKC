package service

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

const (
	maxQuestionLength    = 2000
	messageHistoryLimit  = 100
	assistantSaveTimeout = 5 * time.Second
)

// QAService orchestrates question validation, message persistence, and AI Service streaming.
type QAService interface {
	Ask(ctx context.Context, userID uint64, userUUID string, conversationUUID string, question string) (<-chan SSEEvent, error)
}

// NewQAService creates a QAService.
func NewQAService(aiClient AIClient, convRepo repository.ConversationRepository, msgRepo repository.MessageRepository, logger *zap.Logger) QAService {
	if logger == nil {
		logger = zap.NewNop()
	}
	return &qaService{
		aiClient: aiClient,
		convRepo: convRepo,
		msgRepo:  msgRepo,
		logger:   logger,
	}
}

type qaService struct {
	aiClient AIClient
	convRepo repository.ConversationRepository
	msgRepo  repository.MessageRepository
	logger   *zap.Logger
}

// Ask validates the conversation, persists the user message, and opens a streaming Q&A session.
func (s *qaService) Ask(ctx context.Context, userID uint64, userUUID string, conversationUUID string, question string) (<-chan SSEEvent, error) {
	if strings.TrimSpace(question) == "" || len(question) > maxQuestionLength {
		return nil, apperrors.BadRequest("question must be between 1 and 2000 characters")
	}

	conversation, err := s.convRepo.GetByUUIDAndUserID(ctx, conversationUUID, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.New(http.StatusNotFound, "CONVERSATION_NOT_FOUND", "会话不存在")
		}
		s.logger.Error("failed to load conversation", zap.Error(err))
		return nil, apperrors.Internal("failed to load conversation")
	}

	history, err := s.msgRepo.ListByConversationID(ctx, conversation.ID, messageHistoryLimit)
	if err != nil {
		s.logger.Error("failed to load message history", zap.Error(err))
		return nil, apperrors.Internal("failed to load message history")
	}

	userMsg := &model.Message{
		UUID:           uuid.NewString(),
		ConversationID: conversation.ID,
		Role:           "user",
		Content:        question,
	}
	if err := s.msgRepo.Create(ctx, userMsg); err != nil {
		s.logger.Error("failed to save user message", zap.Error(err))
		return nil, apperrors.Internal("failed to save user message")
	}

	if conversation.Title == "" {
		if err := s.convRepo.UpdateTitle(ctx, conversation.ID, truncate(question, 50)); err != nil {
			s.logger.Warn("failed to update conversation title", zap.Error(err))
		}
	}

	assistantMsgUUID := uuid.NewString()
	req := QARequest{
		Question:       question,
		ConversationID: conversation.UUID,
		MessageID:      assistantMsgUUID,
		UserID:         userUUID,
		ResourceIDs:    parseResourceIDs(conversation.ResourceIDs),
		History:        mapMessagesToHistory(history),
	}

	aiEvents, err := s.aiClient.StreamQA(ctx, req)
	if err != nil {
		return nil, err
	}

	events := make(chan SSEEvent, 64)
	go s.stream(ctx, events, aiEvents, conversation, userMsg, assistantMsgUUID)
	return events, nil
}

func (s *qaService) stream(ctx context.Context, out chan<- SSEEvent, aiEvents <-chan SSEEvent, conversation *model.Conversation, userMsg *model.Message, assistantMsgUUID string) {
	defer close(out)

	var answer strings.Builder
	var citations []any

	for {
		select {
		case <-ctx.Done():
			s.saveAssistant(context.Background(), conversation, userMsg, assistantMsgUUID, answer.String(), citations)
			return
		case ev, ok := <-aiEvents:
			if !ok {
				s.saveAssistant(context.Background(), conversation, userMsg, assistantMsgUUID, answer.String(), citations)
				return
			}
			select {
			case out <- ev:
			default:
			}
			switch ev.Event {
			case "chunk":
				if delta := extractString(ev.Data, "delta"); delta != "" {
					answer.WriteString(delta)
				}
			case "citation":
				if c := parseCitation(ev.Data); c != nil {
					citations = append(citations, c)
				}
			}
			if ev.Event == "done" || ev.Event == "error" {
				s.saveAssistant(context.Background(), conversation, userMsg, assistantMsgUUID, answer.String(), citations)
				return
			}
		}
	}
}

func (s *qaService) saveAssistant(ctx context.Context, conversation *model.Conversation, userMsg *model.Message, assistantMsgUUID string, answer string, citations []any) {
	if answer == "" && len(citations) == 0 {
		return
	}
	ctx, cancel := context.WithTimeout(ctx, assistantSaveTimeout)
	defer cancel()

	var citationsJSON json.RawMessage
	if len(citations) > 0 {
		b, err := json.Marshal(citations)
		if err != nil {
			s.logger.Warn("failed to marshal citations", zap.Error(err))
		} else {
			citationsJSON = b
		}
	}

	assistantMsg := &model.Message{
		UUID:            assistantMsgUUID,
		ConversationID:  conversation.ID,
		ParentMessageID: &userMsg.ID,
		Role:            "assistant",
		Content:         answer,
		Citations:       citationsJSON,
	}
	if err := s.msgRepo.Create(ctx, assistantMsg); err != nil {
		s.logger.Error("failed to save assistant message", zap.Error(err))
	}
	if err := s.convRepo.Touch(ctx, conversation.ID); err != nil {
		s.logger.Warn("failed to touch conversation", zap.Error(err))
	}
}

func truncate(text string, maxLen int) string {
	if len(text) <= maxLen {
		return text
	}
	return text[:maxLen]
}

func parseResourceIDs(raw json.RawMessage) []string {
	if len(raw) == 0 {
		return nil
	}
	var ids []string
	if err := json.Unmarshal(raw, &ids); err != nil {
		return nil
	}
	return ids
}

func mapMessagesToHistory(messages []model.Message) []ChatMessage {
	history := make([]ChatMessage, 0, len(messages))
	for _, m := range messages {
		history = append(history, ChatMessage{Role: m.Role, Content: m.Content})
	}
	return history
}

func extractString(data []byte, key string) string {
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		return ""
	}
	if v, ok := payload[key].(string); ok {
		return v
	}
	return ""
}

func parseCitation(data []byte) map[string]any {
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil
	}
	if _, ok := payload["resource_id"]; !ok {
		return nil
	}
	return payload
}
