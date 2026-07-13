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

// QAOption configures a QAService.
type QAOption func(*qaService)

// WithContextWindowService injects a context-window builder into QAService.
func WithContextWindowService(svc ContextWindowService) QAOption {
	return func(qs *qaService) { qs.ctxWindow = svc }
}

// WithUnitOfWork injects a transaction coordinator into QAService.
func WithUnitOfWork(uow repository.UnitOfWork) QAOption {
	return func(qs *qaService) { qs.uow = uow }
}

// NewQAService creates a QAService.
func NewQAService(aiClient AIClient, convRepo repository.ConversationRepository, msgRepo repository.MessageRepository, logger *zap.Logger, opts ...QAOption) QAService {
	if logger == nil {
		logger = zap.NewNop()
	}
	svc := &qaService{
		aiClient: aiClient,
		convRepo: convRepo,
		msgRepo:  msgRepo,
		logger:   logger,
	}
	for _, opt := range opts {
		opt(svc)
	}
	return svc
}

type qaService struct {
	aiClient  AIClient
	convRepo  repository.ConversationRepository
	msgRepo   repository.MessageRepository
	uow       repository.UnitOfWork
	ctxWindow ContextWindowService
	logger    *zap.Logger
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
		if errors.Is(err, repository.ErrForbidden) {
			return nil, apperrors.Forbidden("无权访问该会话")
		}
		s.logger.Error("failed to load conversation", zap.Error(err))
		return nil, apperrors.Internal("failed to load conversation")
	}

	history, err := s.loadHistory(ctx, conversation, question)
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
	if err := s.saveUserMessageAndTitle(ctx, conversation, userMsg, question); err != nil {
		s.logger.Error("failed to save user message", zap.Error(err))
		return nil, apperrors.Internal("failed to save user message")
	}

	assistantMsgUUID := uuid.NewString()
	req := QARequest{
		Question:       question,
		ConversationID: conversation.UUID,
		MessageID:      assistantMsgUUID,
		UserID:         userUUID,
		ResourceIDs:    parseResourceIDs(conversation.ResourceIDs),
		History:        history,
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
	var reasoning strings.Builder
	var citations []any

	for {
		select {
		case <-ctx.Done():
			s.saveAssistant(context.Background(), conversation, userMsg, assistantMsgUUID, answer.String(), reasoning.String(), citations)
			return
		case ev, ok := <-aiEvents:
			if !ok {
				s.saveAssistant(context.Background(), conversation, userMsg, assistantMsgUUID, answer.String(), reasoning.String(), citations)
				return
			}
			select {
			case out <- ev:
			case <-ctx.Done():
				s.saveAssistant(context.Background(), conversation, userMsg, assistantMsgUUID, answer.String(), reasoning.String(), citations)
				return
			}
			switch ev.Event {
			case "chunk":
				if delta := extractString(ev.Data, "delta"); delta != "" {
					answer.WriteString(delta)
				}
			case "reasoning":
				if delta := extractString(ev.Data, "delta"); delta != "" {
					reasoning.WriteString(delta)
				}
			case "citation":
				if c := parseCitation(ev.Data); c != nil {
					citations = append(citations, c)
				}
			}
			if ev.Event == "done" || ev.Event == "error" {
				s.saveAssistant(context.Background(), conversation, userMsg, assistantMsgUUID, answer.String(), reasoning.String(), citations)
				return
			}
		}
	}
}

func (s *qaService) saveAssistant(ctx context.Context, conversation *model.Conversation, userMsg *model.Message, assistantMsgUUID string, answer string, reasoning string, citations []any) {
	if answer == "" && reasoning == "" && len(citations) == 0 {
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
		Reasoning:       reasoning,
		Citations:       citationsJSON,
		TokenUsage:      estimateTokens(answer),
	}
	if err := s.saveAssistantMessage(ctx, assistantMsg, conversation); err != nil {
		s.logger.Error("failed to save assistant message", zap.Error(err))
	}
}

func (s *qaService) saveUserMessageAndTitle(ctx context.Context, conversation *model.Conversation, userMsg *model.Message, question string) error {
	if s.uow != nil {
		return s.uow.Run(ctx, func(convRepo repository.ConversationRepository, msgRepo repository.MessageRepository) error {
			if err := msgRepo.Create(ctx, userMsg); err != nil {
				return err
			}
			if conversation.Title == "" {
				if err := convRepo.UpdateTitleByIDAndUserID(ctx, conversation.ID, conversation.UserID, truncate(question, 20)); err != nil {
					return err
				}
			}
			return nil
		})
	}
	if err := s.msgRepo.Create(ctx, userMsg); err != nil {
		return err
	}
	if conversation.Title == "" {
		if err := s.convRepo.UpdateTitleByIDAndUserID(ctx, conversation.ID, conversation.UserID, truncate(question, 20)); err != nil {
			return err
		}
	}
	return nil
}

func (s *qaService) saveAssistantMessage(ctx context.Context, assistantMsg *model.Message, conversation *model.Conversation) error {
	if s.uow != nil {
		return s.uow.Run(ctx, func(convRepo repository.ConversationRepository, msgRepo repository.MessageRepository) error {
			if err := msgRepo.Create(ctx, assistantMsg); err != nil {
				return err
			}
			return convRepo.TouchByIDAndUserID(ctx, conversation.ID, conversation.UserID)
		})
	}
	if err := s.msgRepo.Create(ctx, assistantMsg); err != nil {
		return err
	}
	if err := s.convRepo.TouchByIDAndUserID(ctx, conversation.ID, conversation.UserID); err != nil {
		return err
	}
	return nil
}

func (s *qaService) loadHistory(ctx context.Context, conversation *model.Conversation, question string) ([]ChatMessage, error) {
	if s.ctxWindow != nil {
		return s.ctxWindow.BuildMessages(ctx, conversation.ID, question)
	}
	messages, err := s.msgRepo.ListByConversationID(ctx, conversation.ID, messageHistoryLimit)
	if err != nil {
		return nil, err
	}
	return mapMessagesToHistory(messages), nil
}

func truncate(text string, maxLen int) string {
	runes := []rune(text)
	if len(runes) <= maxLen {
		return text
	}
	return string(runes[:maxLen])
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
