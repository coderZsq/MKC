package service

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
)

type stubSummaryResourceRepo struct {
	resource *model.Resource
	err      error
}

func (s *stubSummaryResourceRepo) Create(ctx context.Context, r *model.Resource) error { return nil }
func (s *stubSummaryResourceRepo) GetByUUID(ctx context.Context, uuid string) (*model.Resource, error) {
	if s.err != nil {
		return nil, s.err
	}
	return s.resource, nil
}
func (s *stubSummaryResourceRepo) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
	if s.err != nil {
		return nil, s.err
	}
	return s.resource, nil
}
func (s *stubSummaryResourceRepo) ListByUserID(ctx context.Context, userID uint64, page, limit int, tag string) ([]model.Resource, int64, error) {
	return nil, 0, nil
}
func (s *stubSummaryResourceRepo) CountByUUIDsAndUserID(ctx context.Context, uuids []string, userID uint64) (int64, error) {
	return 0, nil
}
func (s *stubSummaryResourceRepo) UpdateStatus(ctx context.Context, id uint64, status uint8) error {
	return nil
}

type stubSummaryRepo struct {
	saved []model.Summary
	list  []model.Summary
	err   error
}

func (s *stubSummaryRepo) UpsertMany(ctx context.Context, summaries []model.Summary) error {
	s.saved = summaries
	return s.err
}
func (s *stubSummaryRepo) ListByResourceID(ctx context.Context, resourceID uint64) ([]model.Summary, error) {
	return s.list, s.err
}
func (s *stubSummaryRepo) ListFullByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64]*string, error) {
	result := make(map[uint64]*string, len(resourceIDs))
	for _, summary := range s.list {
		if summary.Type == "full" {
			content := summary.Content
			result[summary.ResourceID] = &content
		}
	}
	return result, s.err
}

type stubSummaryTaskRepo struct {
	task *model.Task
	err  error
}

func (s *stubSummaryTaskRepo) Create(ctx context.Context, t *model.Task) error { return nil }
func (s *stubSummaryTaskRepo) GetByUUID(ctx context.Context, uuid string) (*model.Task, error) {
	return nil, repository.ErrNotFound
}
func (s *stubSummaryTaskRepo) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
	return nil, repository.ErrNotFound
}
func (s *stubSummaryTaskRepo) GetLatestCompletedByResourceID(ctx context.Context, resourceID uint64) (*model.Task, error) {
	if s.err != nil {
		return nil, s.err
	}
	return s.task, nil
}
func (s *stubSummaryTaskRepo) ListLatestByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64]model.Task, error) {
	return map[uint64]model.Task{}, nil
}
func (s *stubSummaryTaskRepo) ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error) {
	return nil, 0, nil
}
func (s *stubSummaryTaskRepo) UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
	return nil
}
func (s *stubSummaryTaskRepo) UpdateStatusWithAttempt(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error {
	return nil
}
func (s *stubSummaryTaskRepo) UpdateProgress(ctx context.Context, id uint64, progress uint8) error {
	return nil
}
func (s *stubSummaryTaskRepo) ResetForRetry(ctx context.Context, id uint64) error { return nil }

type stubSummaryDispatcher struct {
	resource *model.Resource
	payload  SummaryDispatchPayload
	err      error
}

func (s *stubSummaryDispatcher) Dispatch(ctx context.Context, task *model.Task, resource *model.Resource) error {
	return nil
}
func (s *stubSummaryDispatcher) DispatchSummary(ctx context.Context, resource *model.Resource, payload SummaryDispatchPayload) error {
	s.resource = resource
	s.payload = payload
	return s.err
}

func (s *stubSummaryDispatcher) DispatchExtraction(ctx context.Context, resource *model.Resource, payload ExtractionDispatchPayload) error {
	return nil
}

func TestSummaryService_SaveInternal(t *testing.T) {
	resourceRepo := &stubSummaryResourceRepo{resource: &model.Resource{ID: 7, UUID: "res-1"}}
	summaryRepo := &stubSummaryRepo{}
	svc := NewSummaryService(nil, resourceRepo, summaryRepo, nil, nil)

	err := svc.SaveInternal(context.Background(), "res-1", SaveSummaryRequest{
		FullSummary: "全文",
		Sections:    []SectionSummary{{Title: "章节", Summary: "章节摘要", PageRange: []int{1, 2}}},
		Model:       "mock",
		Tokens:      12,
	})

	require.NoError(t, err)
	require.Len(t, summaryRepo.saved, 2)
	assert.Equal(t, "full", summaryRepo.saved[0].Type)
	assert.Equal(t, "section", summaryRepo.saved[1].Type)
	assert.Contains(t, string(summaryRepo.saved[1].SectionMeta), "章节")
}

func TestSummaryService_GetByResource(t *testing.T) {
	now := time.Now()
	resourceRepo := &stubSummaryResourceRepo{resource: &model.Resource{ID: 7, UUID: "res-1"}}
	summaryRepo := &stubSummaryRepo{list: []model.Summary{
		{Type: "full", Content: "全文", Model: "mock", UpdatedAt: now},
		{Type: "section", Content: "章节摘要", SectionMeta: []byte(`{"title":"章节","page_range":[1,2]}`), Model: "mock", UpdatedAt: now},
	}}
	svc := NewSummaryService(nil, resourceRepo, summaryRepo, nil, nil)

	result, err := svc.GetByResource(context.Background(), 42, "res-1")

	require.NoError(t, err)
	assert.Equal(t, "res-1", result.ResourceID)
	assert.Equal(t, "全文", result.FullSummary)
	require.Len(t, result.Sections, 1)
	assert.Equal(t, []int{1, 2}, result.Sections[0].PageRange)
}

func TestSummaryService_GetByResource_NotFoundMasksOwnership(t *testing.T) {
	resourceRepo := &stubSummaryResourceRepo{err: repository.ErrNotFound}
	svc := NewSummaryService(nil, resourceRepo, &stubSummaryRepo{}, nil, nil)

	_, err := svc.GetByResource(context.Background(), 42, "missing")

	require.Error(t, err)
	assert.Contains(t, err.Error(), "RESOURCE_NOT_FOUND")
}

func TestSummaryService_TriggerManualSummary(t *testing.T) {
	resource := &model.Resource{ID: 7, UUID: "res-1", Type: model.TaskTypePdfParse}
	resourceRepo := &stubSummaryResourceRepo{resource: resource}
	taskRepo := &stubSummaryTaskRepo{task: &model.Task{
		UUID:       "task-1",
		ResourceID: 7,
		Type:       model.TaskTypePdfParse,
		Status:     model.TaskStatusCompleted,
		Result:     json.RawMessage(`{"toc":[{"title":"概述","page":1}],"pages":[{"text":"正文"}]}`),
	}}
	dispatcher := &stubSummaryDispatcher{}
	svc := NewSummaryService(nil, resourceRepo, &stubSummaryRepo{}, taskRepo, dispatcher)

	result, err := svc.Trigger(context.Background(), 42, "res-1")

	require.NoError(t, err)
	assert.Equal(t, "pending", result.Status)
	assert.Equal(t, "sum-res-1", result.TaskID)
	assert.Equal(t, resource, dispatcher.resource)
	assert.Equal(t, "pdf", dispatcher.payload.SourceType)
	assert.NotNil(t, dispatcher.payload.Parsed)
}
