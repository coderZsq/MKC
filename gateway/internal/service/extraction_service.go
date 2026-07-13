package service

import (
	"context"
	"errors"
	"strings"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

// ExtractionService provides tag/entity persistence and lookup.
type ExtractionService interface {
	SaveInternal(ctx context.Context, resourceUUID string, req SaveExtractionRequest) error
	GetByResource(ctx context.Context, userID uint64, resourceUUID string) (*ResourceExtraction, error)
}

// SaveExtractionRequest carries AI-generated tags and entities.
type SaveExtractionRequest struct {
	Tags     []ResourceTagDTO    `json:"tags"`
	Entities []ResourceEntityDTO `json:"entities"`
	Source   string              `json:"source"`
	Fallback bool                `json:"fallback"`
}

// ResourceTagDTO is the API representation of an extracted tag.
type ResourceTagDTO struct {
	Tag    string `json:"tag"`
	Source string `json:"source,omitempty"`
}

// ResourceEntityDTO is the API representation of an extracted entity.
type ResourceEntityDTO struct {
	Entity  string `json:"entity"`
	Type    string `json:"type"`
	Mention string `json:"mention"`
	Source  string `json:"source,omitempty"`
}

// ResourceExtraction is returned to Web clients.
type ResourceExtraction struct {
	ResourceID string              `json:"resource_id"`
	Tags       []string            `json:"tags"`
	Entities   []ResourceEntityDTO `json:"entities"`
}

type extractionService struct {
	logger         *zap.Logger
	resourceRepo   repository.ResourceRepository
	extractionRepo repository.ExtractionRepository
}

// NewExtractionService creates an ExtractionService.
func NewExtractionService(logger *zap.Logger, resourceRepo repository.ResourceRepository, extractionRepo repository.ExtractionRepository) ExtractionService {
	if logger == nil {
		logger = zap.NewNop()
	}
	return &extractionService{logger: logger, resourceRepo: resourceRepo, extractionRepo: extractionRepo}
}

// SaveInternal persists tags and entities reported by the AI Service.
func (s *extractionService) SaveInternal(ctx context.Context, resourceUUID string, req SaveExtractionRequest) error {
	resource, err := s.resourceRepo.GetByUUID(ctx, resourceUUID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return apperrors.New(404, "RESOURCE_NOT_FOUND", "resource not found")
		}
		s.logger.Error("failed to get resource for extraction save", zap.Error(err))
		return apperrors.Internal("internal server error")
	}

	source := normalizeExtractionSource(req.Source)
	tags := make([]model.ResourceTag, 0, len(req.Tags))
	for _, item := range req.Tags {
		tag := strings.TrimSpace(item.Tag)
		if tag == "" {
			continue
		}
		itemSource := normalizeExtractionSource(item.Source)
		if itemSource == "" {
			itemSource = source
		}
		tags = append(tags, model.ResourceTag{ResourceID: resource.ID, Tag: tag, Source: itemSource})
	}

	entities := make([]model.ResourceEntity, 0, len(req.Entities))
	for _, item := range req.Entities {
		entity := strings.TrimSpace(item.Entity)
		entityType := strings.ToUpper(strings.TrimSpace(item.Type))
		mention := strings.TrimSpace(item.Mention)
		if entity == "" || entityType == "" || mention == "" {
			continue
		}
		itemSource := normalizeExtractionSource(item.Source)
		if itemSource == "" {
			itemSource = source
		}
		entities = append(entities, model.ResourceEntity{
			ResourceID: resource.ID,
			Entity:     entity,
			Type:       entityType,
			Mention:    mention,
			Source:     itemSource,
		})
	}

	if err := s.extractionRepo.UpsertTags(ctx, resource.ID, tags); err != nil {
		s.logger.Error("failed to save resource tags", zap.Error(err))
		return apperrors.Internal("internal server error")
	}
	if err := s.extractionRepo.UpsertEntities(ctx, resource.ID, entities); err != nil {
		s.logger.Error("failed to save resource entities", zap.Error(err))
		return apperrors.Internal("internal server error")
	}
	return nil
}

// GetByResource returns extracted tags and entities after checking ownership.
func (s *extractionService) GetByResource(ctx context.Context, userID uint64, resourceUUID string) (*ResourceExtraction, error) {
	resource, err := s.resourceRepo.GetByUUIDAndUserID(ctx, resourceUUID, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.New(404, "RESOURCE_NOT_FOUND", "resource not found")
		}
		s.logger.Error("failed to get resource for extraction", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	tagRecords, err := s.extractionRepo.ListTagsByResourceID(ctx, resource.ID)
	if err != nil {
		s.logger.Error("failed to list resource tags", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}
	entityRecords, err := s.extractionRepo.ListEntitiesByResourceID(ctx, resource.ID)
	if err != nil {
		s.logger.Error("failed to list resource entities", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	result := &ResourceExtraction{
		ResourceID: resource.UUID,
		Tags:       make([]string, 0, len(tagRecords)),
		Entities:   make([]ResourceEntityDTO, 0, len(entityRecords)),
	}
	for _, record := range tagRecords {
		result.Tags = append(result.Tags, record.Tag)
	}
	for _, record := range entityRecords {
		result.Entities = append(result.Entities, ResourceEntityDTO{
			Entity:  record.Entity,
			Type:    record.Type,
			Mention: record.Mention,
		})
	}
	return result, nil
}

func normalizeExtractionSource(source string) string {
	switch strings.ToLower(strings.TrimSpace(source)) {
	case "rule":
		return "rule"
	case "llm":
		return "llm"
	default:
		return "llm"
	}
}
