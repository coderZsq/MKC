package repository

import (
	"context"
	"fmt"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// MessageRepository defines data access operations for conversation messages.
type MessageRepository interface {
	Create(ctx context.Context, m *model.Message) error
	ListByConversationID(ctx context.Context, conversationID uint64, limit int) ([]model.Message, error)
	ListByConversationIDPaginated(ctx context.Context, conversationID uint64, page, limit int) ([]model.Message, int64, error)
}

// GORMMessageRepository is a GORM-backed MessageRepository.
type GORMMessageRepository struct {
	db *gorm.DB
}

// NewMessageRepository creates a new GORM message repository.
func NewMessageRepository(db *gorm.DB) MessageRepository {
	return &GORMMessageRepository{db: db}
}

// Create inserts a new message record.
func (r *GORMMessageRepository) Create(ctx context.Context, m *model.Message) error {
	if err := r.db.WithContext(ctx).Create(m).Error; err != nil {
		return fmt.Errorf("failed to create message: %w", err)
	}
	return nil
}

// ListByConversationID returns messages for a conversation ordered oldest first.
func (r *GORMMessageRepository) ListByConversationID(ctx context.Context, conversationID uint64, limit int) ([]model.Message, error) {
	if limit <= 0 {
		limit = 100
	}
	var messages []model.Message
	if err := r.db.WithContext(ctx).
		Where("conversation_id = ?", conversationID).
		Order("created_at ASC, id ASC").
		Limit(limit).
		Find(&messages).Error; err != nil {
		return nil, fmt.Errorf("failed to list messages: %w", err)
	}
	return messages, nil
}

// ListByConversationIDPaginated returns paginated messages ordered oldest first.
func (r *GORMMessageRepository) ListByConversationIDPaginated(ctx context.Context, conversationID uint64, page, limit int) ([]model.Message, int64, error) {
	if page <= 0 {
		page = 1
	}
	if limit <= 0 {
		limit = 20
	}
	var total int64
	if err := r.db.WithContext(ctx).Model(&model.Message{}).Where("conversation_id = ?", conversationID).Count(&total).Error; err != nil {
		return nil, 0, fmt.Errorf("failed to count messages: %w", err)
	}
	offset := (page - 1) * limit
	var messages []model.Message
	if err := r.db.WithContext(ctx).
		Where("conversation_id = ?", conversationID).
		Order("created_at ASC, id ASC").
		Limit(limit).
		Offset(offset).
		Find(&messages).Error; err != nil {
		return nil, 0, fmt.Errorf("failed to list messages: %w", err)
	}
	return messages, total, nil
}
