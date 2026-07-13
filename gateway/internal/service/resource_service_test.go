package service

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
)

type stubResourceListRepo struct {
	resources []model.Resource
	total     int64
	tag       string
	err       error
}

func (s *stubResourceListRepo) ListByUserID(ctx context.Context, userID uint64, page, limit int, tag string) ([]model.Resource, int64, error) {
	s.tag = tag
	return s.resources, s.total, s.err
}

type stubTaskRepoForResource struct {
	tasks map[uint64]model.Task
}

func (s *stubTaskRepoForResource) Create(ctx context.Context, t *model.Task) error { return nil }
func (s *stubTaskRepoForResource) GetByUUID(ctx context.Context, uuid string) (*model.Task, error) {
	return nil, nil
}
func (s *stubTaskRepoForResource) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
	return nil, nil
}
func (s *stubTaskRepoForResource) GetLatestCompletedByResourceID(ctx context.Context, resourceID uint64) (*model.Task, error) {
	return nil, nil
}
func (s *stubTaskRepoForResource) ListLatestByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64]model.Task, error) {
	return s.tasks, nil
}
func (s *stubTaskRepoForResource) ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error) {
	return nil, 0, nil
}
func (s *stubTaskRepoForResource) UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
	return nil
}
func (s *stubTaskRepoForResource) UpdateStatusWithAttempt(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error {
	return nil
}
func (s *stubTaskRepoForResource) UpdateProgress(ctx context.Context, id uint64, progress uint8) error {
	return nil
}
func (s *stubTaskRepoForResource) ResetForRetry(ctx context.Context, id uint64) error { return nil }

func TestResourceService_ListAggregatesSummaryAndTags(t *testing.T) {
	updatedAt := time.Date(2026, 7, 12, 10, 30, 0, 0, time.UTC)
	resourceRepo := &stubResourceListRepo{
		resources: []model.Resource{{ID: 7, UUID: "res-1", Name: "report.pdf", Type: "pdf_parse", Status: 3, UpdatedAt: updatedAt}},
		total:     1,
	}
	summary := "这是摘要"
	summaryRepo := &stubSummaryRepo{list: []model.Summary{{ResourceID: 7, Type: "full", Content: summary}}}
	extractionRepo := &stubExtractionRepo{tags: []model.ResourceTag{{ResourceID: 7, Tag: "机器学习"}}}
	taskRepo := &stubTaskRepoForResource{tasks: map[uint64]model.Task{7: {UUID: "task-1", ResourceID: 7}}}
	svc := NewResourceService(nil, resourceRepo, taskRepo, summaryRepo, extractionRepo)

	result, err := svc.List(context.Background(), 42, ListResourcesRequest{Page: 1, Limit: 20, Tag: " 机器学习 "})

	require.NoError(t, err)
	assert.Equal(t, "机器学习", resourceRepo.tag)
	require.Len(t, result.Items, 1)
	assert.Equal(t, "res-1", result.Items[0].ResourceID)
	assert.Equal(t, "task-1", result.Items[0].TaskID)
	assert.Equal(t, "completed", result.Items[0].Status)
	require.NotNil(t, result.Items[0].Summary)
	assert.Equal(t, summary, *result.Items[0].Summary)
	assert.Equal(t, []string{"机器学习"}, result.Items[0].Tags)
	assert.Equal(t, int64(1), result.Total)
}

func TestResourceService_ListRejectsLongTag(t *testing.T) {
	svc := NewResourceService(nil, &stubResourceListRepo{}, &stubTaskRepoForResource{}, &stubSummaryRepo{}, &stubExtractionRepo{})

	_, err := svc.List(context.Background(), 42, ListResourcesRequest{Page: 1, Limit: 20, Tag: "abcdefghijklmnopqrstuvwxyz1234567"})

	require.Error(t, err)
	assert.Contains(t, err.Error(), "tag length")
}
