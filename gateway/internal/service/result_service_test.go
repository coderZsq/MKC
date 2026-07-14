package service

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"github.com/zhushuangquan/mkc/gateway/internal/storage"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type stubTaskRepo struct {
	getByUUIDAndUserIDFunc             func(ctx context.Context, uuid string, userID uint64) (*model.Task, error)
	getLatestCompletedByResourceIDFunc func(ctx context.Context, resourceID uint64) (*model.Task, error)
}

func (r *stubTaskRepo) Create(ctx context.Context, t *model.Task) error { return nil }
func (r *stubTaskRepo) GetByUUID(ctx context.Context, uuid string) (*model.Task, error) {
	return nil, nil
}
func (r *stubTaskRepo) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
	if r.getByUUIDAndUserIDFunc != nil {
		return r.getByUUIDAndUserIDFunc(ctx, uuid, userID)
	}
	return nil, repository.ErrNotFound
}
func (r *stubTaskRepo) GetLatestCompletedByResourceID(ctx context.Context, resourceID uint64) (*model.Task, error) {
	if r.getLatestCompletedByResourceIDFunc != nil {
		return r.getLatestCompletedByResourceIDFunc(ctx, resourceID)
	}
	return nil, repository.ErrNotFound
}
func (r *stubTaskRepo) ListLatestByResourceIDs(ctx context.Context, resourceIDs []uint64) (map[uint64]model.Task, error) {
	return map[uint64]model.Task{}, nil
}
func (r *stubTaskRepo) ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error) {
	return nil, 0, nil
}
func (r *stubTaskRepo) UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
	return nil
}
func (r *stubTaskRepo) UpdateProgress(ctx context.Context, id uint64, progress uint8) error {
	return nil
}
func (r *stubTaskRepo) UpdateStatusWithAttempt(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error {
	return nil
}
func (r *stubTaskRepo) ResetForRetry(ctx context.Context, id uint64) error { return nil }

var _ repository.TaskRepository = (*stubTaskRepo)(nil)

type stubResourceRepo struct {
	getByUUIDAndUserIDFunc func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error)
}

func (r *stubResourceRepo) Create(ctx context.Context, res *model.Resource) error { return nil }
func (r *stubResourceRepo) GetByUUID(ctx context.Context, uuid string) (*model.Resource, error) {
	return nil, repository.ErrNotFound
}
func (r *stubResourceRepo) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
	if r.getByUUIDAndUserIDFunc != nil {
		return r.getByUUIDAndUserIDFunc(ctx, uuid, userID)
	}
	return nil, repository.ErrNotFound
}
func (r *stubResourceRepo) ListByUserID(ctx context.Context, userID uint64, page, limit int, tag string) ([]model.Resource, int64, error) {
	return nil, 0, nil
}
func (r *stubResourceRepo) CountByUUIDsAndUserID(ctx context.Context, uuids []string, userID uint64) (int64, error) {
	return 0, nil
}
func (r *stubResourceRepo) UpdateStatus(ctx context.Context, id uint64, status uint8) error { return nil }

var _ repository.ResourceRepository = (*stubResourceRepo)(nil)

type stubResultStorage struct {
	presignedURL string
	err          error
}

func (s *stubResultStorage) PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error {
	return nil
}
func (s *stubResultStorage) RemoveObject(ctx context.Context, key string) error { return nil }
func (s *stubResultStorage) PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	return s.presignedURL, s.err
}

var _ storage.ObjectStorage = (*stubResultStorage)(nil)

func TestResultService_GetResult_Success(t *testing.T) {
	repo := &stubTaskRepo{
		getByUUIDAndUserIDFunc: func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
			return &model.Task{
				UUID:   uuid,
				UserID: userID,
				Status: model.TaskStatusCompleted,
				Result: json.RawMessage(`{
					"transcript_url": "minio://mkc-resources/results/task-1/transcript.json",
					"subtitle_url": "minio://mkc-resources/results/task-1/subtitle.srt",
					"metadata": {"duration": 3600, "word_count": 5000}
				}`),
			}, nil
		},
	}
	storage := &stubResultStorage{presignedURL: "https://minio/presigned"}
	svc := NewResultService(nil, repo, nil, storage, time.Hour, "mkc-resources")

	result, err := svc.GetResult(context.Background(), 42, "task-1")

	require.NoError(t, err)
	assert.Equal(t, "task-1", result.TaskID)
	assert.Equal(t, model.TaskStatusCompleted, result.Status)
	require.NotNil(t, result.Files.TranscriptURL)
	assert.Equal(t, "https://minio/presigned", *result.Files.TranscriptURL)
	require.NotNil(t, result.Files.SubtitleURL)
	assert.Equal(t, "https://minio/presigned", *result.Files.SubtitleURL)
	assert.Nil(t, result.Files.ParsedURL)
	assert.Equal(t, 3600.0, result.Metadata["duration"])
}

func TestResultService_GetResult_TaskNotFound(t *testing.T) {
	repo := &stubTaskRepo{}
	svc := NewResultService(nil, repo, nil, &stubResultStorage{}, time.Hour, "mkc-resources")

	_, err := svc.GetResult(context.Background(), 42, "missing")

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, 404, appErr.Status)
	assert.Equal(t, apperrors.CodeNotFound, appErr.Code)
}

func TestResultService_GetResult_NotCompleted(t *testing.T) {
	repo := &stubTaskRepo{
		getByUUIDAndUserIDFunc: func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
			return &model.Task{UUID: uuid, UserID: userID, Status: model.TaskStatusRunning}, nil
		},
	}
	svc := NewResultService(nil, repo, nil, &stubResultStorage{}, time.Hour, "mkc-resources")

	_, err := svc.GetResult(context.Background(), 42, "task-1")

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, 400, appErr.Status)
	assert.Equal(t, apperrors.CodeTaskNotCompleted, appErr.Code)
}

func TestResultService_GetResult_BucketMismatch(t *testing.T) {
	repo := &stubTaskRepo{
		getByUUIDAndUserIDFunc: func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
			return &model.Task{
				UUID:   uuid,
				Status: model.TaskStatusCompleted,
				Result: json.RawMessage(`{"transcript_url": "minio://other-bucket/results/task-1/transcript.json"}`),
			}, nil
		},
	}
	storage := &stubResultStorage{presignedURL: "https://minio/presigned"}
	svc := NewResultService(nil, repo, nil, storage, time.Hour, "mkc-resources")

	result, err := svc.GetResult(context.Background(), 42, "task-1")

	require.NoError(t, err)
	assert.Nil(t, result.Files.TranscriptURL)
}

func TestResultService_GetResult_PresignFailure(t *testing.T) {
	repo := &stubTaskRepo{
		getByUUIDAndUserIDFunc: func(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
			return &model.Task{
				UUID:   uuid,
				Status: model.TaskStatusCompleted,
				Result: json.RawMessage(`{"transcript_url": "minio://mkc-resources/results/task-1/transcript.json"}`),
			}, nil
		},
	}
	storage := &stubResultStorage{err: errors.New("minio unavailable")}
	svc := NewResultService(nil, repo, nil, storage, time.Hour, "mkc-resources")

	result, err := svc.GetResult(context.Background(), 42, "task-1")

	require.NoError(t, err)
	assert.Nil(t, result.Files.TranscriptURL)
}

func TestResultService_GetResultByResourceID_Success(t *testing.T) {
	resourceRepo := &stubResourceRepo{
		getByUUIDAndUserIDFunc: func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
			assert.Equal(t, "res-1", uuid)
			assert.Equal(t, uint64(42), userID)
			return &model.Resource{ID: 7, UUID: uuid, UserID: userID}, nil
		},
	}
	taskRepo := &stubTaskRepo{
		getLatestCompletedByResourceIDFunc: func(ctx context.Context, resourceID uint64) (*model.Task, error) {
			assert.Equal(t, uint64(7), resourceID)
			return &model.Task{
				UUID:       "task-7",
				ResourceID: 7,
				UserID:     42,
				Status:     model.TaskStatusCompleted,
				Result:     json.RawMessage(`{"parsed_url": "minio://mkc-resources/results/task-7/parsed.md"}`),
			}, nil
		},
	}
	storage := &stubResultStorage{presignedURL: "https://minio/presigned"}
	svc := NewResultService(nil, taskRepo, resourceRepo, storage, time.Hour, "mkc-resources")

	result, err := svc.GetResultByResourceID(context.Background(), 42, "res-1")

	require.NoError(t, err)
	assert.Equal(t, "task-7", result.TaskID)
	require.NotNil(t, result.Files.ParsedURL)
	assert.Equal(t, "https://minio/presigned", *result.Files.ParsedURL)
}

func TestResultService_GetResultByResourceID_ResourceNotFound(t *testing.T) {
	resourceRepo := &stubResourceRepo{}
	taskRepo := &stubTaskRepo{}
	svc := NewResultService(nil, taskRepo, resourceRepo, &stubResultStorage{}, time.Hour, "mkc-resources")

	_, err := svc.GetResultByResourceID(context.Background(), 42, "missing")

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, 404, appErr.Status)
	assert.Equal(t, apperrors.CodeNotFound, appErr.Code)
}

func TestResultService_GetResultByResourceID_TaskNotCompleted(t *testing.T) {
	resourceRepo := &stubResourceRepo{
		getByUUIDAndUserIDFunc: func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
			return &model.Resource{ID: 7, UUID: uuid, UserID: userID}, nil
		},
	}
	taskRepo := &stubTaskRepo{
		getLatestCompletedByResourceIDFunc: func(ctx context.Context, resourceID uint64) (*model.Task, error) {
			return &model.Task{UUID: "task-7", ResourceID: 7, UserID: 42, Status: model.TaskStatusRunning}, nil
		},
	}
	svc := NewResultService(nil, taskRepo, resourceRepo, &stubResultStorage{}, time.Hour, "mkc-resources")

	_, err := svc.GetResultByResourceID(context.Background(), 42, "res-1")

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, 400, appErr.Status)
	assert.Equal(t, apperrors.CodeTaskNotCompleted, appErr.Code)
}

func TestParseMinIOURL(t *testing.T) {
	bucket, key, err := parseMinIOURL("minio://mkc-resources/results/task-1/file.json")
	require.NoError(t, err)
	assert.Equal(t, "mkc-resources", bucket)
	assert.Equal(t, "results/task-1/file.json", key)
}

func TestParseMinIOURL_Invalid(t *testing.T) {
	_, _, err := parseMinIOURL("not-a-url")
	require.Error(t, err)
}
