package service

import (
	"context"
	"errors"
	"strings"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

const maxResourceTagLength = 32

// ResourceListRepository defines resource list access for the resource API.
type ResourceListRepository interface {
	ListByUserID(ctx context.Context, userID uint64, page, limit int, tag string) ([]model.Resource, int64, error)
}

// ResourceService provides authenticated resource list operations.
type ResourceService interface {
	List(ctx context.Context, userID uint64, req ListResourcesRequest) (*ListResourcesResult, error)
}

// ListResourcesRequest carries resource list filters.
type ListResourcesRequest struct {
	Page  int
	Limit int
	Tag   string
}

// ListResourcesResult is returned by the resource list operation.
type ListResourcesResult struct {
	Items []ResourceListItem
	Total int64
}

// ResourceListItem is returned to Web clients.
type ResourceListItem struct {
	ResourceID       string    `json:"resource_id"`
	Name             string    `json:"name"`
	Type             string    `json:"type"`
	Status           string    `json:"status"`
	Summary          *string   `json:"summary"`
	SummaryTruncated bool      `json:"summary_truncated"`
	Tags             []string  `json:"tags"`
	UpdatedAt        time.Time `json:"updated_at"`
}

type resourceService struct {
	logger         *zap.Logger
	resourceRepo   ResourceListRepository
	summaryRepo    repository.SummaryRepository
	extractionRepo repository.ExtractionRepository
}

// NewResourceService creates a ResourceService.
func NewResourceService(logger *zap.Logger, resourceRepo ResourceListRepository, summaryRepo repository.SummaryRepository, extractionRepo repository.ExtractionRepository) ResourceService {
	if logger == nil {
		logger = zap.NewNop()
	}
	return &resourceService{logger: logger, resourceRepo: resourceRepo, summaryRepo: summaryRepo, extractionRepo: extractionRepo}
}

// List returns resources with latest full summary and tags.
func (s *resourceService) List(ctx context.Context, userID uint64, req ListResourcesRequest) (*ListResourcesResult, error) {
	tag := strings.TrimSpace(req.Tag)
	if len([]rune(tag)) > maxResourceTagLength {
		return nil, apperrors.New(400, apperrors.CodeValidationError, "tag length exceeds limit")
	}

	resources, total, err := s.resourceRepo.ListByUserID(ctx, userID, req.Page, req.Limit, tag)
	if err != nil {
		s.logger.Error("failed to list resources", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}
	if len(resources) == 0 {
		return &ListResourcesResult{Items: []ResourceListItem{}, Total: total}, nil
	}

	resourceIDs := make([]uint64, 0, len(resources))
	for _, resource := range resources {
		resourceIDs = append(resourceIDs, resource.ID)
	}

	summaries, err := s.summaryRepo.ListFullByResourceIDs(ctx, resourceIDs)
	if err != nil && !errors.Is(err, repository.ErrNotFound) {
		s.logger.Error("failed to list resource summaries", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}
	tags, err := s.extractionRepo.ListTagsByResourceIDs(ctx, resourceIDs)
	if err != nil {
		s.logger.Error("failed to list resource tags", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	items := make([]ResourceListItem, 0, len(resources))
	for _, resource := range resources {
		items = append(items, ResourceListItem{
			ResourceID:       resource.UUID,
			Name:             resource.Name,
			Type:             resource.Type,
			Status:           resourceStatusLabel(resource.Status),
			Summary:          summaries[resource.ID],
			SummaryTruncated: false,
			Tags:             tags[resource.ID],
			UpdatedAt:        resource.UpdatedAt,
		})
	}
	return &ListResourcesResult{Items: items, Total: total}, nil
}

func resourceStatusLabel(status uint8) string {
	switch status {
	case 1:
		return "uploading"
	case 2:
		return "processing"
	case 3:
		return "completed"
	case 4:
		return "failed"
	default:
		return "unknown"
	}
}
