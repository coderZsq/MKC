package repository

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"gorm.io/gorm"
)

// UserRepository defines data access operations for users.
type UserRepository interface {
	Create(ctx context.Context, user *model.User) error
	GetByEmail(ctx context.Context, email string) (*model.User, error)
	GetByUUID(ctx context.Context, uuid string) (*model.User, error)
}

// GORMUserRepository is a GORM-backed UserRepository.
type GORMUserRepository struct {
	db *gorm.DB
}

// NewUserRepository creates a new GORM user repository.
func NewUserRepository(db *gorm.DB) UserRepository {
	return &GORMUserRepository{db: db}
}

func (r *GORMUserRepository) Create(ctx context.Context, user *model.User) error {
	if err := r.db.WithContext(ctx).Create(user).Error; err != nil {
		if errors.Is(err, gorm.ErrDuplicatedKey) || isDuplicateKeyError(err) {
			return apperrors.Conflict("email already exists")
		}
		return fmt.Errorf("failed to create user: %w", err)
	}
	return nil
}

func isDuplicateKeyError(err error) bool {
	msg := err.Error()
	return strings.Contains(strings.ToLower(msg), "duplicate") ||
		strings.Contains(strings.ToLower(msg), "unique constraint failed")
}

func (r *GORMUserRepository) GetByEmail(ctx context.Context, email string) (*model.User, error) {
	var user model.User
	if err := r.db.WithContext(ctx).Where("email = ?", email).First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get user by email: %w", err)
	}
	return &user, nil
}

func (r *GORMUserRepository) GetByUUID(ctx context.Context, uuid string) (*model.User, error) {
	var user model.User
	if err := r.db.WithContext(ctx).Where("uuid = ?", uuid).First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("failed to get user by uuid: %w", err)
	}
	return &user, nil
}
