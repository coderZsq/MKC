package repository

import (
	"context"
	"fmt"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// ExtractionRepository defines data access operations for tags and entities.
type ExtractionRepository interface {
	UpsertTags(ctx context.Context, resourceID uint64, tags []model.ResourceTag) error
	UpsertEntities(ctx context.Context, resourceID uint64, entities []model.ResourceEntity) error
	ListTagsByResourceID(ctx context.Context, resourceID uint64) ([]model.ResourceTag, error)
	ListTagsByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64][]string, error)
	ListEntitiesByResourceID(ctx context.Context, resourceID uint64) ([]model.ResourceEntity, error)
}

// GORMExtractionRepository is a GORM-backed ExtractionRepository.
type GORMExtractionRepository struct {
	db *gorm.DB
}

// NewExtractionRepository creates a new extraction repository.
func NewExtractionRepository(db *gorm.DB) ExtractionRepository {
	return &GORMExtractionRepository{db: db}
}

// UpsertTags replaces tags for a resource.
func (r *GORMExtractionRepository) UpsertTags(ctx context.Context, resourceID uint64, tags []model.ResourceTag) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Where("resource_id = ?", resourceID).Delete(&model.ResourceTag{}).Error; err != nil {
			return fmt.Errorf("failed to delete old tags: %w", err)
		}
		if len(tags) == 0 {
			return nil
		}
		if err := tx.Create(&tags).Error; err != nil {
			return fmt.Errorf("failed to create tags: %w", err)
		}
		return nil
	})
}

// UpsertEntities replaces entities for a resource.
func (r *GORMExtractionRepository) UpsertEntities(ctx context.Context, resourceID uint64, entities []model.ResourceEntity) error {
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Where("resource_id = ?", resourceID).Delete(&model.ResourceEntity{}).Error; err != nil {
			return fmt.Errorf("failed to delete old entities: %w", err)
		}
		if len(entities) == 0 {
			return nil
		}
		if err := tx.Create(&entities).Error; err != nil {
			return fmt.Errorf("failed to create entities: %w", err)
		}
		return nil
	})
}

// ListTagsByResourceID returns tags for a resource.
func (r *GORMExtractionRepository) ListTagsByResourceID(ctx context.Context, resourceID uint64) ([]model.ResourceTag, error) {
	var tags []model.ResourceTag
	if err := r.db.WithContext(ctx).
		Where("resource_id = ?", resourceID).
		Order("id ASC").
		Find(&tags).Error; err != nil {
		return nil, fmt.Errorf("failed to list tags: %w", err)
	}
	return tags, nil
}

// ListTagsByResourceIDs returns tags keyed by resource ID.
func (r *GORMExtractionRepository) ListTagsByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64][]string, error) {
	result := make(map[uint64][]string, len(resourceIDs))
	if len(resourceIDs) == 0 {
		return result, nil
	}
	var tags []model.ResourceTag
	if err := r.db.WithContext(ctx).
		Where("resource_id IN ?", resourceIDs).
		Order("resource_id ASC, id ASC").
		Find(&tags).Error; err != nil {
		return nil, fmt.Errorf("failed to list tags: %w", err)
	}
	for _, tag := range tags {
		result[tag.ResourceID] = append(result[tag.ResourceID], tag.Tag)
	}
	return result, nil
}

// ListEntitiesByResourceID returns entities for a resource.
func (r *GORMExtractionRepository) ListEntitiesByResourceID(ctx context.Context, resourceID uint64) ([]model.ResourceEntity, error) {
	var entities []model.ResourceEntity
	if err := r.db.WithContext(ctx).
		Where("resource_id = ?", resourceID).
		Order("id ASC").
		Find(&entities).Error; err != nil {
		return nil, fmt.Errorf("failed to list entities: %w", err)
	}
	return entities, nil
}
