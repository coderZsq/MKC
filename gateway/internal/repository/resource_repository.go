package repository

import (
	"context"
	"fmt"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/gorm"
)

// ResourceRepository defines data access operations for resources.
type ResourceRepository interface {
	Create(ctx context.Context, r *model.Resource) error
	UpdateStatus(ctx context.Context, id uint64, status uint8) error
}

// GORMResourceRepository is a GORM-backed ResourceRepository.
type GORMResourceRepository struct {
	db *gorm.DB
}

// NewResourceRepository creates a new GORM resource repository.
func NewResourceRepository(db *gorm.DB) ResourceRepository {
	return &GORMResourceRepository{db: db}
}

// Create inserts a new resource record.
func (r *GORMResourceRepository) Create(ctx context.Context, resource *model.Resource) error {
	if err := r.db.WithContext(ctx).Create(resource).Error; err != nil {
		return fmt.Errorf("failed to create resource: %w", err)
	}
	return nil
}

// UpdateStatus updates the status of a resource by ID.
func (r *GORMResourceRepository) UpdateStatus(ctx context.Context, id uint64, status uint8) error {
	if err := r.db.WithContext(ctx).
		Model(&model.Resource{}).
		Where("id = ?", id).
		Update("status", status).Error; err != nil {
		return fmt.Errorf("failed to update resource status: %w", err)
	}
	return nil
}
