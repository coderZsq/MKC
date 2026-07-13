package repository

import (
	"context"
	"errors"
	"fmt"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// SummaryRepository defines data access operations for resource summaries.
type SummaryRepository interface {
	UpsertMany(ctx context.Context, summaries []model.Summary) error
	ListByResourceID(ctx context.Context, resourceID uint64) ([]model.Summary, error)
	ListFullByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64]*string, error)
}

// GORMSummaryRepository is a GORM-backed SummaryRepository.
type GORMSummaryRepository struct {
	db *gorm.DB
}

// NewSummaryRepository creates a new summary repository.
func NewSummaryRepository(db *gorm.DB) SummaryRepository {
	return &GORMSummaryRepository{db: db}
}

// UpsertMany replaces all summaries for a resource.
func (r *GORMSummaryRepository) UpsertMany(ctx context.Context, summaries []model.Summary) error {
	if len(summaries) == 0 {
		return nil
	}
	resourceID := summaries[0].ResourceID
	return r.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Where("resource_id = ?", resourceID).Delete(&model.Summary{}).Error; err != nil {
			return fmt.Errorf("failed to delete old summaries: %w", err)
		}
		if err := tx.Create(&summaries).Error; err != nil {
			return fmt.Errorf("failed to create summaries: %w", err)
		}
		return nil
	})
}

// ListByResourceID returns all summaries for a resource.
func (r *GORMSummaryRepository) ListByResourceID(ctx context.Context, resourceID uint64) ([]model.Summary, error) {
	var summaries []model.Summary
	if err := r.db.WithContext(ctx).
		Where("resource_id = ?", resourceID).
		Order("type ASC, id ASC").
		Find(&summaries).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to list summaries: %w", err)
	}
	return summaries, nil
}

// ListFullByResourceIDs returns full summaries keyed by resource ID.
func (r *GORMSummaryRepository) ListFullByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64]*string, error) {
	result := make(map[uint64]*string, len(resourceIDs))
	if len(resourceIDs) == 0 {
		return result, nil
	}
	var summaries []model.Summary
	if err := r.db.WithContext(ctx).
		Where("resource_id IN ? AND type = ?", resourceIDs, "full").
		Order("updated_at DESC, id DESC").
		Find(&summaries).Error; err != nil {
		return nil, fmt.Errorf("failed to list full summaries: %w", err)
	}
	for _, summary := range summaries {
		if _, exists := result[summary.ResourceID]; exists {
			continue
		}
		content := summary.Content
		result[summary.ResourceID] = &content
	}
	return result, nil
}
