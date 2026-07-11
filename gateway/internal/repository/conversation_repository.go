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
	ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Conversation, int64, error)
	UpdateTitleByIDAndUserID(ctx context.Context, id uint64, userID uint64, title string) error
	TouchByIDAndUserID(ctx context.Context, id uint64, userID uint64) error
	DeleteByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) error
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
	if err := r.db.WithContext(ctx).Where("uuid = ?", uuid).First(&conversation).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get conversation by uuid: %w", err)
	}
	if conversation.UserID != userID {
		return nil, ErrForbidden
	}
	return &conversation, nil
}

// ListByUserID returns paginated conversations for a user ordered by updated_at desc.
func (r *GORMConversationRepository) ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Conversation, int64, error) {
	if page <= 0 {
		page = 1
	}
	if limit <= 0 {
		limit = 20
	}
	var total int64
	if err := r.db.WithContext(ctx).Model(&model.Conversation{}).Where("user_id = ?", userID).Count(&total).Error; err != nil {
		return nil, 0, fmt.Errorf("failed to count conversations: %w", err)
	}
	var conversations []model.Conversation
	offset := (page - 1) * limit
	if err := r.db.WithContext(ctx).
		Where("user_id = ?", userID).
		Order("updated_at DESC, id DESC").
		Limit(limit).
		Offset(offset).
		Find(&conversations).Error; err != nil {
		return nil, 0, fmt.Errorf("failed to list conversations: %w", err)
	}
	return conversations, total, nil
}

// UpdateTitleByIDAndUserID updates the conversation title only if it belongs to the user.
func (r *GORMConversationRepository) UpdateTitleByIDAndUserID(ctx context.Context, id uint64, userID uint64, title string) error {
	var conversation model.Conversation
	if err := r.db.WithContext(ctx).Where("id = ?", id).First(&conversation).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return ErrNotFound
		}
		return fmt.Errorf("failed to get conversation before update title: %w", err)
	}
	if conversation.UserID != userID {
		return ErrForbidden
	}
	if err := r.db.WithContext(ctx).
		Model(&model.Conversation{}).
		Where("id = ? AND user_id = ?", id, userID).
		Update("title", title).Error; err != nil {
		return fmt.Errorf("failed to update conversation title: %w", err)
	}
	return nil
}

// TouchByIDAndUserID updates the conversation updated_at timestamp only if it belongs to the user.
func (r *GORMConversationRepository) TouchByIDAndUserID(ctx context.Context, id uint64, userID uint64) error {
	var conversation model.Conversation
	if err := r.db.WithContext(ctx).Where("id = ?", id).First(&conversation).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return ErrNotFound
		}
		return fmt.Errorf("failed to get conversation before touch: %w", err)
	}
	if conversation.UserID != userID {
		return ErrForbidden
	}
	if err := r.db.WithContext(ctx).
		Model(&model.Conversation{}).
		Where("id = ? AND user_id = ?", id, userID).
		Update("updated_at", time.Now()).Error; err != nil {
		return fmt.Errorf("failed to touch conversation: %w", err)
	}
	return nil
}

// DeleteByUUIDAndUserID removes a conversation by UUID only if it belongs to the user.
// Cascading deletes are handled by the foreign key on messages.
func (r *GORMConversationRepository) DeleteByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) error {
	var conversation model.Conversation
	if err := r.db.WithContext(ctx).Where("uuid = ?", uuid).First(&conversation).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return ErrNotFound
		}
		return fmt.Errorf("failed to get conversation before delete: %w", err)
	}
	if conversation.UserID != userID {
		return ErrForbidden
	}
	if err := r.db.WithContext(ctx).Unscoped().Where("uuid = ? AND user_id = ?", uuid, userID).Delete(&model.Conversation{}).Error; err != nil {
		return fmt.Errorf("failed to delete conversation: %w", err)
	}
	return nil
}
