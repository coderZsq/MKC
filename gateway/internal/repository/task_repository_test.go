package repository

import (
	"context"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
)

func newTestTask(resourceID, userID uint64, taskType string) *model.Task {
	return &model.Task{
		UUID:       uuid.NewString(),
		ResourceID: resourceID,
		UserID:     userID,
		Type:       taskType,
		Status:     "pending",
		CreatedAt:  time.Now(),
		UpdatedAt:  time.Now(),
	}
}

func TestTaskRepository_Create(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	user := newTestUser("taskowner@example.com", "hashed", "Owner")
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	resource := newTestResource(user.ID, "song.mp3", "audio/mpeg")
	require.NoError(t, db.WithContext(ctx).Create(resource).Error)

	task := newTestTask(resource.ID, user.ID, "media_parse")
	err := repo.Create(ctx, task)
	require.NoError(t, err)
	assert.NotZero(t, task.ID)

	var stored struct {
		UUID       string
		ResourceID uint64 `gorm:"column:resource_id"`
		Type       string
		Status     string
	}
	require.NoError(t, db.WithContext(ctx).Model(&model.Task{}).Select("uuid", "resource_id", "type", "status").First(&stored, task.ID).Error)
	assert.Equal(t, task.UUID, stored.UUID)
	assert.Equal(t, resource.ID, stored.ResourceID)
	assert.Equal(t, "pending", stored.Status)
}

func TestTaskRepository_Create_WithoutResourceFails(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	user := newTestUser("taskowner2@example.com", "hashed", "Owner2")
	require.NoError(t, db.WithContext(ctx).Create(user).Error)

	task := newTestTask(9999, user.ID, "media_parse")
	err := repo.Create(ctx, task)
	require.Error(t, err)
}
