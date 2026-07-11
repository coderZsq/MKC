package service

import (
	"context"
	"fmt"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
)

// ContextWindowService builds a context window within a token budget.
type ContextWindowService interface {
	BuildMessages(ctx context.Context, conversationID uint64, question string) ([]ChatMessage, error)
}

// NewContextWindowService creates a ContextWindowService.
func NewContextWindowService(msgRepo repository.MessageRepository, maxContextMessages, maxContextTokens int) ContextWindowService {
	if maxContextMessages <= 0 {
		maxContextMessages = 20
	}
	if maxContextTokens <= 0 {
		maxContextTokens = 4096
	}
	return &contextWindowService{
		msgRepo:            msgRepo,
		maxContextMessages: maxContextMessages,
		maxContextTokens:   maxContextTokens,
	}
}

type contextWindowService struct {
	msgRepo            repository.MessageRepository
	maxContextMessages int
	maxContextTokens   int
}

func (s *contextWindowService) BuildMessages(ctx context.Context, conversationID uint64, question string) ([]ChatMessage, error) {
	messages, err := s.msgRepo.ListByConversationID(ctx, conversationID, s.maxContextMessages)
	if err != nil {
		return nil, fmt.Errorf("failed to load context messages: %w", err)
	}

	total := estimateTokens(question)
	selected := make([]model.Message, 0, len(messages))
	for i := len(messages) - 1; i >= 0; i-- {
		tokens := estimateTokens(messages[i].Content)
		if total+tokens > s.maxContextTokens {
			break
		}
		selected = append([]model.Message{messages[i]}, selected...)
		total += tokens
	}
	return mapMessagesToHistory(selected), nil
}

func estimateTokens(content string) int {
	return (len([]rune(content)) + 1) / 2
}
