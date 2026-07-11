package repository

import (
	"context"

	"gorm.io/gorm"
)

// UnitOfWork runs a block of repository operations inside a single database transaction.
type UnitOfWork interface {
	Run(ctx context.Context, fn func(ConversationRepository, MessageRepository) error) error
}

type gormUnitOfWork struct {
	db *gorm.DB
}

// NewUnitOfWork creates a UnitOfWork backed by GORM.
func NewUnitOfWork(db *gorm.DB) UnitOfWork {
	return &gormUnitOfWork{db: db}
}

func (u *gormUnitOfWork) Run(ctx context.Context, fn func(ConversationRepository, MessageRepository) error) error {
	return u.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		return fn(NewConversationRepository(tx), NewMessageRepository(tx))
	})
}
