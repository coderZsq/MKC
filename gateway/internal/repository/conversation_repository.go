package repository

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// ConversationRepository defines data access operations for conversations.
type ConversationRepository interface {
	Create(ctx context.Context, c *model.Conversation) error
	GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Conversation, error)
	UpdateTitle(ctx context.Context, id uint64, title string) error
	Touch(ctx context.Context, id uint64) error
}

// GORMConversationRepository is a GORM-backed ConversationRepository.
type GORMConversationRepository struct {
	db *gorm.DB
}

// NewConversationRepository creates a new GORM conversation repository.
func NewConversationRepository(db *gorm.DB) ConversationRepository {
	return &GORMConversationRepository{db: db}
}

// Create inserts a new conversation record.
func (r *GORMConversationRepository) Create(ctx context.Context, c *model.Conversation) error {
	if err := r.db.WithContext(ctx).Create(c).Error; err != nil {
		return fmt.Errorf("failed to create conversation: %w", err)
	}
	return nil
}

// GetByUUIDAndUserID fetches a conversation by UUID and ensures it belongs to the user.
func (r *GORMConversationRepository) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Conversation, error) {
	var conversation model.Conversation
	if err := r.db.WithContext(ctx).Where("uuid = ? AND user_id = ?", uuid, userID).First(&conversation).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get conversation by uuid and user: %w", err)
	}
	return &conversation, nil
}

// UpdateTitle updates the conversation title.
func (r *GORMConversationRepository) UpdateTitle(ctx context.Context, id uint64, title string) error {
	if err := r.db.WithContext(ctx).
		Model(&model.Conversation{}).
		Where("id = ?", id).
		Update("title", title).Error; err != nil {
		return fmt.Errorf("failed to update conversation title: %w", err)
	}
	return nil
}

// Touch updates the conversation updated_at timestamp.
func (r *GORMConversationRepository) Touch(ctx context.Context, id uint64) error {
	if err := r.db.WithContext(ctx).
		Model(&model.Conversation{}).
		Where("id = ?", id).
		Update("updated_at", time.Now()).Error; err != nil {
		return fmt.Errorf("failed to touch conversation: %w", err)
	}
	return nil
}
