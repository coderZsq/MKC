package service

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
)

type stubExtractionResourceRepo struct {
	resource *model.Resource
	err      error
}

func (s *stubExtractionResourceRepo) Create(ctx context.Context, resource *model.Resource) error {
	return nil
}
func (s *stubExtractionResourceRepo) GetByUUID(ctx context.Context, uuid string) (*model.Resource, error) {
	return s.resource, s.err
}
func (s *stubExtractionResourceRepo) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
	return s.resource, s.err
}
func (s *stubExtractionResourceRepo) ListByUserID(ctx context.Context, userID uint64, page, limit int, tag string) ([]model.Resource, int64, error) {
	return nil, 0, nil
}
func (s *stubExtractionResourceRepo) CountByUUIDsAndUserID(ctx context.Context, uuids []string, userID uint64) (int64, error) {
	return 0, nil
}
func (s *stubExtractionResourceRepo) UpdateStatus(ctx context.Context, id uint64, status uint8) error {
	return nil
}

var _ repository.ResourceRepository = (*stubExtractionResourceRepo)(nil)

type stubExtractionRepo struct {
	tags     []model.ResourceTag
	entities []model.ResourceEntity
}

func (s *stubExtractionRepo) UpsertTags(ctx context.Context, resourceID uint64, tags []model.ResourceTag) error {
	s.tags = tags
	return nil
}
func (s *stubExtractionRepo) UpsertEntities(ctx context.Context, resourceID uint64, entities []model.ResourceEntity) error {
	s.entities = entities
	return nil
}
func (s *stubExtractionRepo) ListTagsByResourceID(ctx context.Context, resourceID uint64) ([]model.ResourceTag, error) {
	return s.tags, nil
}
func (s *stubExtractionRepo) ListTagsByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64][]string, error) {
	result := make(map[uint64][]string)
	for _, tag := range s.tags {
		result[tag.ResourceID] = append(result[tag.ResourceID], tag.Tag)
	}
	return result, nil
}
func (s *stubExtractionRepo) ListEntitiesByResourceID(ctx context.Context, resourceID uint64) ([]model.ResourceEntity, error) {
	return s.entities, nil
}

var _ repository.ExtractionRepository = (*stubExtractionRepo)(nil)

func TestExtractionService_SaveInternal(t *testing.T) {
	resourceRepo := &stubExtractionResourceRepo{resource: &model.Resource{ID: 7, UUID: "res-1"}}
	extractionRepo := &stubExtractionRepo{}
	svc := NewExtractionService(nil, resourceRepo, extractionRepo)

	err := svc.SaveInternal(context.Background(), "res-1", SaveExtractionRequest{
		Tags:     []ResourceTagDTO{{Tag: " 机器学习 ", Source: "llm"}, {Tag: ""}},
		Entities: []ResourceEntityDTO{{Entity: " OpenAI ", Type: "org", Mention: "OpenAI"}},
		Source:   "llm",
	})

	require.NoError(t, err)
	require.Len(t, extractionRepo.tags, 1)
	assert.Equal(t, "机器学习", extractionRepo.tags[0].Tag)
	require.Len(t, extractionRepo.entities, 1)
	assert.Equal(t, "ORG", extractionRepo.entities[0].Type)
}

func TestExtractionService_GetByResource(t *testing.T) {
	resourceRepo := &stubExtractionResourceRepo{resource: &model.Resource{ID: 7, UUID: "res-1"}}
	extractionRepo := &stubExtractionRepo{
		tags:     []model.ResourceTag{{Tag: "机器学习"}},
		entities: []model.ResourceEntity{{Entity: "OpenAI", Type: "ORG", Mention: "OpenAI"}},
	}
	svc := NewExtractionService(nil, resourceRepo, extractionRepo)

	result, err := svc.GetByResource(context.Background(), 42, "res-1")

	require.NoError(t, err)
	assert.Equal(t, "res-1", result.ResourceID)
	assert.Equal(t, []string{"机器学习"}, result.Tags)
	require.Len(t, result.Entities, 1)
	assert.Equal(t, "OpenAI", result.Entities[0].Entity)
}

func TestExtractionService_GetByResource_NotFound(t *testing.T) {
	resourceRepo := &stubExtractionResourceRepo{err: repository.ErrNotFound}
	svc := NewExtractionService(nil, resourceRepo, &stubExtractionRepo{})

	_, err := svc.GetByResource(context.Background(), 42, "missing")

	require.Error(t, err)
	assert.Contains(t, err.Error(), "resource not found")
}
