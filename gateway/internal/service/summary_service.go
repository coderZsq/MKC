package service

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

// SummaryService provides summary persistence and lookup.
type SummaryService interface {
	SaveInternal(ctx context.Context, resourceUUID string, req SaveSummaryRequest) error
	GetByResource(ctx context.Context, userID uint64, resourceUUID string) (*ResourceSummary, error)
	Trigger(ctx context.Context, userID uint64, resourceUUID string) (*TriggerSummaryResult, error)
}

// SaveSummaryRequest carries AI-generated summaries.
type SaveSummaryRequest struct {
	FullSummary string           `json:"full_summary"`
	Sections    []SectionSummary `json:"sections"`
	Model       string           `json:"model"`
	Tokens      int              `json:"tokens"`
	Fallback    bool             `json:"fallback"`
}

// SectionSummary is the API representation of a section summary.
type SectionSummary struct {
	Title          string    `json:"title"`
	Summary        string    `json:"summary"`
	PageRange      []int     `json:"page_range,omitempty"`
	TimestampRange []float64 `json:"timestamp_range,omitempty"`
}

// ResourceSummary is returned to Web clients.
type ResourceSummary struct {
	ResourceID  string           `json:"resource_id"`
	FullSummary string           `json:"full_summary"`
	Sections    []SectionSummary `json:"sections"`
	Model       string           `json:"model"`
	Fallback    bool             `json:"fallback"`
	UpdatedAt   time.Time        `json:"updated_at"`
}

// TriggerSummaryResult is returned after queuing a manual summary task.
type TriggerSummaryResult struct {
	ResourceID string `json:"resource_id"`
	TaskID     string `json:"task_id"`
	Status     string `json:"status"`
}

type summaryService struct {
	logger       *zap.Logger
	resourceRepo repository.ResourceRepository
	summaryRepo  repository.SummaryRepository
	taskRepo     repository.TaskRepository
	dispatcher   TaskDispatcher
}

// NewSummaryService creates a SummaryService.
func NewSummaryService(logger *zap.Logger, resourceRepo repository.ResourceRepository, summaryRepo repository.SummaryRepository, taskRepo repository.TaskRepository, dispatcher TaskDispatcher) SummaryService {
	if logger == nil {
		logger = zap.NewNop()
	}
	return &summaryService{logger: logger, resourceRepo: resourceRepo, summaryRepo: summaryRepo, taskRepo: taskRepo, dispatcher: dispatcher}
}

// SaveInternal persists summaries reported by the AI Service.
func (s *summaryService) SaveInternal(ctx context.Context, resourceUUID string, req SaveSummaryRequest) error {
	resource, err := s.resourceRepo.GetByUUID(ctx, resourceUUID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return apperrors.New(404, "RESOURCE_NOT_FOUND", "resource not found")
		}
		s.logger.Error("failed to get resource for summary save", zap.Error(err))
		return apperrors.Internal("internal server error")
	}

	records := make([]model.Summary, 0, 1+len(req.Sections))
	if req.FullSummary != "" {
		records = append(records, model.Summary{
			ResourceID: resource.ID,
			Type:       "full",
			Content:    req.FullSummary,
			Model:      req.Model,
			Tokens:     req.Tokens,
			Fallback:   req.Fallback,
		})
	}
	for _, section := range req.Sections {
		meta, err := json.Marshal(sectionMeta{
			Title:          section.Title,
			PageRange:      section.PageRange,
			TimestampRange: section.TimestampRange,
		})
		if err != nil {
			return apperrors.BadRequest("invalid section metadata")
		}
		records = append(records, model.Summary{
			ResourceID:  resource.ID,
			Type:        "section",
			Content:     section.Summary,
			SectionMeta: meta,
			Model:       req.Model,
			Tokens:      req.Tokens,
			Fallback:    req.Fallback,
		})
	}
	if len(records) == 0 {
		return apperrors.BadRequest("summary content is empty")
	}

	if err := s.summaryRepo.UpsertMany(ctx, records); err != nil {
		s.logger.Error("failed to save summaries", zap.Error(err))
		return apperrors.Internal("internal server error")
	}
	return nil
}

// GetByResource returns a resource summary after checking ownership.
func (s *summaryService) GetByResource(ctx context.Context, userID uint64, resourceUUID string) (*ResourceSummary, error) {
	resource, err := s.resourceRepo.GetByUUIDAndUserID(ctx, resourceUUID, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.New(404, "RESOURCE_NOT_FOUND", "resource not found")
		}
		s.logger.Error("failed to get resource for summary", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	records, err := s.summaryRepo.ListByResourceID(ctx, resource.ID)
	if err != nil {
		s.logger.Error("failed to list summaries", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}
	if len(records) == 0 {
		return nil, apperrors.New(404, "SUMMARY_NOT_FOUND", "summary not found")
	}

	result := &ResourceSummary{ResourceID: resource.UUID, Sections: []SectionSummary{}}
	for _, record := range records {
		if record.UpdatedAt.After(result.UpdatedAt) {
			result.UpdatedAt = record.UpdatedAt
		}
		if result.Model == "" {
			result.Model = record.Model
		}
		result.Fallback = result.Fallback || record.Fallback
		if record.Type == "full" {
			result.FullSummary = record.Content
			continue
		}
		var meta sectionMeta
		_ = json.Unmarshal(record.SectionMeta, &meta)
		result.Sections = append(result.Sections, SectionSummary{
			Title:          meta.Title,
			Summary:        record.Content,
			PageRange:      meta.PageRange,
			TimestampRange: meta.TimestampRange,
		})
	}
	return result, nil
}

// Trigger queues summary generation for the latest completed parse task.
func (s *summaryService) Trigger(ctx context.Context, userID uint64, resourceUUID string) (*TriggerSummaryResult, error) {
	if s.dispatcher == nil {
		return nil, apperrors.WorkerUnavailable("AI service is unavailable")
	}
	resource, err := s.resourceRepo.GetByUUIDAndUserID(ctx, resourceUUID, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.New(404, "RESOURCE_NOT_FOUND", "resource not found")
		}
		s.logger.Error("failed to get resource for summary trigger", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}
	task, err := s.taskRepo.GetLatestCompletedByResourceID(ctx, resource.ID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.New(409, "SUMMARY_SOURCE_NOT_READY", "resource processing is not completed")
		}
		s.logger.Error("failed to get latest completed task for summary trigger", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}
	task.Resource = *resource
	payload, ok := buildSummaryPayload(task, task.Result, false)
	if !ok {
		return nil, apperrors.New(409, "SUMMARY_SOURCE_NOT_READY", "summary source is not ready")
	}
	if err := s.dispatcher.DispatchSummary(ctx, resource, payload); err != nil {
		return nil, err
	}
	return &TriggerSummaryResult{ResourceID: resource.UUID, TaskID: payload.TaskID, Status: "pending"}, nil
}

type sectionMeta struct {
	Title          string    `json:"title"`
	PageRange      []int     `json:"page_range,omitempty"`
	TimestampRange []float64 `json:"timestamp_range,omitempty"`
}
