package service

import (
	"context"
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

func TestResourceService_ListAggregatesSummaryAndTags(t *testing.T) {
	updatedAt := time.Date(2026, 7, 12, 10, 30, 0, 0, time.UTC)
	resourceRepo := &stubResourceListRepo{
		resources: []model.Resource{{ID: 7, UUID: "res-1", Name: "report.pdf", Type: "pdf_parse", Status: 3, UpdatedAt: updatedAt}},
		total:     1,
	}
	summary := "这是摘要"
	summaryRepo := &stubSummaryRepo{list: []model.Summary{{ResourceID: 7, Type: "full", Content: summary}}}
	extractionRepo := &stubExtractionRepo{tags: []model.ResourceTag{{ResourceID: 7, Tag: "机器学习"}}}
	svc := NewResourceService(nil, resourceRepo, summaryRepo, extractionRepo)

	result, err := svc.List(context.Background(), 42, ListResourcesRequest{Page: 1, Limit: 20, Tag: " 机器学习 "})

	require.NoError(t, err)
	assert.Equal(t, "机器学习", resourceRepo.tag)
	require.Len(t, result.Items, 1)
	assert.Equal(t, "res-1", result.Items[0].ResourceID)
	assert.Equal(t, "completed", result.Items[0].Status)
	require.NotNil(t, result.Items[0].Summary)
	assert.Equal(t, summary, *result.Items[0].Summary)
	assert.Equal(t, []string{"机器学习"}, result.Items[0].Tags)
	assert.Equal(t, int64(1), result.Total)
}

func TestResourceService_ListRejectsLongTag(t *testing.T) {
	svc := NewResourceService(nil, &stubResourceListRepo{}, &stubSummaryRepo{}, &stubExtractionRepo{})

	_, err := svc.List(context.Background(), 42, ListResourcesRequest{Page: 1, Limit: 20, Tag: "abcdefghijklmnopqrstuvwxyz1234567"})

	require.Error(t, err)
	assert.Contains(t, err.Error(), "tag length")
}
