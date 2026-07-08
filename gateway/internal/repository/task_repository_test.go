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
		Status:     model.TaskStatusPending,
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
	assert.Equal(t, model.TaskStatusPending, stored.Status)
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

func TestTaskRepository_GetByUUID(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	user := newTestUser("owner@example.com", "hashed", "Owner")
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	resource := newTestResource(user.ID, "doc.txt", "text/plain")
	require.NoError(t, db.WithContext(ctx).Create(resource).Error)
	task := newTestTask(resource.ID, user.ID, "document_parse")
	require.NoError(t, db.WithContext(ctx).Create(task).Error)

	found, err := repo.GetByUUID(ctx, task.UUID)
	require.NoError(t, err)
	assert.Equal(t, task.UUID, found.UUID)
	assert.Equal(t, resource.UUID, found.Resource.UUID)
}

func TestTaskRepository_GetByUUID_NotFound(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	_, err := repo.GetByUUID(ctx, uuid.NewString())
	assert.ErrorIs(t, err, ErrNotFound)
}

func TestTaskRepository_GetByUUIDAndUserID(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	userA := newTestUser("a@example.com", "hashed", "A")
	userB := newTestUser("b@example.com", "hashed", "B")
	require.NoError(t, db.WithContext(ctx).Create(userA).Error)
	require.NoError(t, db.WithContext(ctx).Create(userB).Error)

	resource := newTestResource(userA.ID, "doc.txt", "text/plain")
	require.NoError(t, db.WithContext(ctx).Create(resource).Error)
	task := newTestTask(resource.ID, userA.ID, "document_parse")
	require.NoError(t, db.WithContext(ctx).Create(task).Error)

	found, err := repo.GetByUUIDAndUserID(ctx, task.UUID, userA.ID)
	require.NoError(t, err)
	assert.Equal(t, task.UUID, found.UUID)

	_, err = repo.GetByUUIDAndUserID(ctx, task.UUID, userB.ID)
	assert.ErrorIs(t, err, ErrNotFound)
}

func TestTaskRepository_ListByUserID(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	userA := newTestUser("a@example.com", "hashed", "A")
	userB := newTestUser("b@example.com", "hashed", "B")
	require.NoError(t, db.WithContext(ctx).Create(userA).Error)
	require.NoError(t, db.WithContext(ctx).Create(userB).Error)

	resourceA := newTestResource(userA.ID, "a.txt", "text/plain")
	resourceA.UUID = uuid.NewString()
	resourceB := newTestResource(userB.ID, "b.txt", "text/plain")
	resourceB.UUID = uuid.NewString()
	require.NoError(t, db.WithContext(ctx).Create(resourceA).Error)
	require.NoError(t, db.WithContext(ctx).Create(resourceB).Error)

	for i := 0; i < 3; i++ {
		task := newTestTask(resourceA.ID, userA.ID, "document_parse")
		require.NoError(t, db.WithContext(ctx).Create(task).Error)
	}
	taskB := newTestTask(resourceB.ID, userB.ID, "document_parse")
	require.NoError(t, db.WithContext(ctx).Create(taskB).Error)

	tasks, total, err := repo.ListByUserID(ctx, userA.ID, 1, 2)
	require.NoError(t, err)
	assert.Equal(t, int64(3), total)
	assert.Len(t, tasks, 2)
	for _, task := range tasks {
		assert.Equal(t, userA.ID, task.UserID)
	}
}

func TestTaskRepository_UpdateStatus(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	user := newTestUser("owner@example.com", "hashed", "Owner")
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	resource := newTestResource(user.ID, "doc.txt", "text/plain")
	require.NoError(t, db.WithContext(ctx).Create(resource).Error)
	task := newTestTask(resource.ID, user.ID, "document_parse")
	require.NoError(t, db.WithContext(ctx).Create(task).Error)

	err := repo.UpdateStatus(ctx, task.ID, model.TaskStatusRunning, 0, nil, "")
	require.NoError(t, err)

	var updated model.Task
	require.NoError(t, db.WithContext(ctx).First(&updated, task.ID).Error)
	assert.Equal(t, model.TaskStatusRunning, updated.Status)
	assert.NotNil(t, updated.StartedAt)

	err = repo.UpdateStatus(ctx, task.ID, model.TaskStatusCompleted, 100, nil, "")
	require.NoError(t, err)
	require.NoError(t, db.WithContext(ctx).First(&updated, task.ID).Error)
	assert.Equal(t, model.TaskStatusCompleted, updated.Status)
	assert.NotNil(t, updated.CompletedAt)

	err = repo.UpdateStatus(ctx, task.ID, model.TaskStatusFailed, 0, nil, "boom")
	require.NoError(t, err)
	require.NoError(t, db.WithContext(ctx).First(&updated, task.ID).Error)
	assert.Equal(t, model.TaskStatusFailed, updated.Status)
	assert.Equal(t, "boom", updated.ErrorMessage)
}

func TestTaskRepository_UpdateProgress(t *testing.T) {
	db := setupResourceTestDB(t)
	repo := NewTaskRepository(db)
	ctx := context.Background()

	user := newTestUser("owner@example.com", "hashed", "Owner")
	require.NoError(t, db.WithContext(ctx).Create(user).Error)
	resource := newTestResource(user.ID, "doc.txt", "text/plain")
	require.NoError(t, db.WithContext(ctx).Create(resource).Error)
	task := newTestTask(resource.ID, user.ID, "document_parse")
	task.Status = model.TaskStatusRunning
	require.NoError(t, db.WithContext(ctx).Create(task).Error)

	err := repo.UpdateProgress(ctx, task.ID, 50)
	require.NoError(t, err)

	var updated model.Task
	require.NoError(t, db.WithContext(ctx).First(&updated, task.ID).Error)
	assert.Equal(t, uint8(50), updated.Progress)
}
