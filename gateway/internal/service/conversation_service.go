package service

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

const (
	maxTitleLength      = 255
	maxResourceIDs      = 100
	maxModelConfigBytes = 4096
	maxMessageContent   = 10000
	maxMessageModel     = 64
)

// CreateConversationRequest is the payload for creating a conversation.
type CreateConversationRequest struct {
	Title       string         `json:"title"`
	ResourceIDs []string       `json:"resource_ids"`
	ModelConfig map[string]any `json:"model_config,omitempty"`
}

// CreateMessageRequest is the payload for creating a message.
type CreateMessageRequest struct {
	Role    string `json:"role"`
	Content string `json:"content"`
	Model   string `json:"model,omitempty"`
}

// ConversationResponse is the API representation of a conversation.
type ConversationResponse struct {
	ID          string         `json:"id"`
	Title       string         `json:"title"`
	ResourceIDs []string       `json:"resource_ids,omitempty"`
	ModelConfig map[string]any `json:"model_config,omitempty"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
}

// MessageResponse is the API representation of a message.
type MessageResponse struct {
	ID        string           `json:"id"`
	Role      string           `json:"role"`
	Content   string           `json:"content"`
	Model     string           `json:"model,omitempty"`
	Citations []map[string]any `json:"citations,omitempty"`
	CreatedAt time.Time        `json:"created_at"`
}

// MessageListResponse is a paginated message list.
type MessageListResponse struct {
	Items []MessageResponse `json:"items"`
	Total int64             `json:"total"`
	Page  int               `json:"page"`
	Limit int               `json:"limit"`
}

// ConversationService manages conversation and message persistence.
type ConversationService interface {
	Create(ctx context.Context, userID uint64, req CreateConversationRequest) (*ConversationResponse, error)
	List(ctx context.Context, userID uint64, page, limit int) ([]ConversationResponse, int64, error)
	Get(ctx context.Context, userID uint64, id string) (*ConversationResponse, error)
	Delete(ctx context.Context, userID uint64, id string) error
	ListMessages(ctx context.Context, userID uint64, conversationID string, page, limit int) (*MessageListResponse, error)
	CreateMessage(ctx context.Context, userID uint64, conversationID string, req CreateMessageRequest) (*MessageResponse, error)
}

// NewConversationService creates a ConversationService.
func NewConversationService(convRepo repository.ConversationRepository, msgRepo repository.MessageRepository, resourceRepo repository.ResourceRepository, uow repository.UnitOfWork, defaultTitle string, logger *zap.Logger) ConversationService {
	if logger == nil {
		logger = zap.NewNop()
	}
	if defaultTitle == "" {
		defaultTitle = "新会话"
	}
	return &conversationService{
		convRepo:     convRepo,
		msgRepo:      msgRepo,
		resourceRepo: resourceRepo,
		uow:          uow,
		defaultTitle: defaultTitle,
		logger:       logger,
	}
}

type conversationService struct {
	convRepo     repository.ConversationRepository
	msgRepo      repository.MessageRepository
	resourceRepo repository.ResourceRepository
	uow          repository.UnitOfWork
	defaultTitle string
	logger       *zap.Logger
}

func (s *conversationService) Create(ctx context.Context, userID uint64, req CreateConversationRequest) (*ConversationResponse, error) {
	if err := validateCreateConversationRequest(ctx, req, userID, s.resourceRepo); err != nil {
		return nil, err
	}
	title := req.Title
	if title == "" {
		title = s.defaultTitle
	}
	var resourceRaw json.RawMessage
	if len(req.ResourceIDs) > 0 {
		b, err := json.Marshal(req.ResourceIDs)
		if err != nil {
			return nil, apperrors.BadRequest("invalid resource_ids")
		}
		resourceRaw = b
	}
	var modelConfigRaw json.RawMessage
	if len(req.ModelConfig) > 0 {
		b, err := json.Marshal(req.ModelConfig)
		if err != nil {
			return nil, apperrors.BadRequest("invalid model_config")
		}
		modelConfigRaw = b
	}
	conv := &model.Conversation{
		UUID:        uuid.NewString(),
		UserID:      userID,
		Title:       title,
		ResourceIDs: resourceRaw,
		ModelConfig: modelConfigRaw,
	}
	if err := s.convRepo.Create(ctx, conv); err != nil {
		return nil, apperrors.Internal("failed to create conversation")
	}
	return s.mapConversation(conv), nil
}

func (s *conversationService) List(ctx context.Context, userID uint64, page, limit int) ([]ConversationResponse, int64, error) {
	conversations, total, err := s.convRepo.ListByUserID(ctx, userID, page, limit)
	if err != nil {
		return nil, 0, apperrors.Internal("failed to list conversations")
	}
	responses := make([]ConversationResponse, len(conversations))
	for i, c := range conversations {
		responses[i] = *s.mapConversation(&c)
	}
	return responses, total, nil
}

func (s *conversationService) Get(ctx context.Context, userID uint64, id string) (*ConversationResponse, error) {
	conv, err := s.convRepo.GetByUUIDAndUserID(ctx, id, userID)
	if err != nil {
		return nil, mapConversationRepositoryError(err)
	}
	return s.mapConversation(conv), nil
}

func (s *conversationService) Delete(ctx context.Context, userID uint64, id string) error {
	if err := s.convRepo.DeleteByUUIDAndUserID(ctx, id, userID); err != nil {
		return mapConversationRepositoryError(err)
	}
	return nil
}

func (s *conversationService) ListMessages(ctx context.Context, userID uint64, conversationID string, page, limit int) (*MessageListResponse, error) {
	conv, err := s.convRepo.GetByUUIDAndUserID(ctx, conversationID, userID)
	if err != nil {
		return nil, mapConversationRepositoryError(err)
	}
	messages, total, err := s.msgRepo.ListByConversationIDPaginated(ctx, conv.ID, page, limit)
	if err != nil {
		return nil, apperrors.Internal("failed to list messages")
	}
	items := make([]MessageResponse, len(messages))
	for i, m := range messages {
		items[i] = *s.mapMessage(&m)
	}
	return &MessageListResponse{
		Items: items,
		Total: total,
		Page:  page,
		Limit: limit,
	}, nil
}

func (s *conversationService) CreateMessage(ctx context.Context, userID uint64, conversationID string, req CreateMessageRequest) (*MessageResponse, error) {
	if err := validateCreateMessageRequest(req); err != nil {
		return nil, err
	}
	conv, err := s.convRepo.GetByUUIDAndUserID(ctx, conversationID, userID)
	if err != nil {
		return nil, mapConversationRepositoryError(err)
	}
	msg := &model.Message{
		UUID:           uuid.NewString(),
		ConversationID: conv.ID,
		Role:           req.Role,
		Content:        req.Content,
		Model:          req.Model,
	}
	if err := s.uow.Run(ctx, func(convRepo repository.ConversationRepository, msgRepo repository.MessageRepository) error {
		if err := msgRepo.Create(ctx, msg); err != nil {
			return err
		}
		return convRepo.TouchByIDAndUserID(ctx, conv.ID, userID)
	}); err != nil {
		return nil, apperrors.Internal("failed to create message")
	}
	return s.mapMessage(msg), nil
}

func (s *conversationService) mapConversation(c *model.Conversation) *ConversationResponse {
	var resourceIDs []string
	if len(c.ResourceIDs) > 0 {
		if err := json.Unmarshal(c.ResourceIDs, &resourceIDs); err != nil {
			s.logger.Warn("failed to unmarshal resource_ids", zap.Error(err))
		}
	}
	var modelConfig map[string]any
	if len(c.ModelConfig) > 0 {
		if err := json.Unmarshal(c.ModelConfig, &modelConfig); err != nil {
			s.logger.Warn("failed to unmarshal model_config", zap.Error(err))
		}
	}
	return &ConversationResponse{
		ID:          c.UUID,
		Title:       c.Title,
		ResourceIDs: resourceIDs,
		ModelConfig: modelConfig,
		CreatedAt:   c.CreatedAt,
		UpdatedAt:   c.UpdatedAt,
	}
}

func (s *conversationService) mapMessage(m *model.Message) *MessageResponse {
	var citations []map[string]any
	if len(m.Citations) > 0 {
		if err := json.Unmarshal(m.Citations, &citations); err != nil {
			s.logger.Warn("failed to unmarshal citations", zap.Error(err))
		}
	}
	return &MessageResponse{
		ID:        m.UUID,
		Role:      m.Role,
		Content:   m.Content,
		Model:     m.Model,
		Citations: citations,
		CreatedAt: m.CreatedAt,
	}
}

func mapConversationRepositoryError(err error) error {
	if err == nil {
		return nil
	}
	if errors.Is(err, repository.ErrNotFound) {
		return apperrors.New(http.StatusNotFound, "CONVERSATION_NOT_FOUND", "会话不存在")
	}
	if errors.Is(err, repository.ErrForbidden) {
		return apperrors.Forbidden("无权访问该会话")
	}
	return apperrors.Internal("failed to load conversation")
}

func validateCreateConversationRequest(ctx context.Context, req CreateConversationRequest, userID uint64, resourceRepo repository.ResourceRepository) error {
	if len(req.Title) > maxTitleLength {
		return apperrors.BadRequest("title exceeds 255 characters")
	}
	if len(req.ResourceIDs) > maxResourceIDs {
		return apperrors.BadRequest("too many resource_ids")
	}
	if len(req.ResourceIDs) > 0 && resourceRepo != nil {
		count, err := resourceRepo.CountByUUIDsAndUserID(ctx, req.ResourceIDs, userID)
		if err != nil {
			return apperrors.Internal("failed to validate resource_ids")
		}
		if count != int64(len(req.ResourceIDs)) {
			return apperrors.BadRequest("invalid resource_ids")
		}
	}
	if len(req.ModelConfig) > 0 {
		b, err := json.Marshal(req.ModelConfig)
		if err != nil {
			return apperrors.BadRequest("invalid model_config")
		}
		if len(b) > maxModelConfigBytes {
			return apperrors.BadRequest("model_config exceeds 4KB")
		}
	}
	return nil
}

func validateCreateMessageRequest(req CreateMessageRequest) error {
	if req.Role != "user" {
		return apperrors.BadRequest("message role must be user")
	}
	if req.Content == "" {
		return apperrors.BadRequest("message content is required")
	}
	if len(req.Content) > maxMessageContent {
		return apperrors.BadRequest("message content exceeds 10000 characters")
	}
	if len(req.Model) > maxMessageModel {
		return apperrors.BadRequest("model exceeds 64 characters")
	}
	return nil
}
