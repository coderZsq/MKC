package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"regexp"
	"strings"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"github.com/zhushuangquan/mkc/gateway/internal/storage"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

var minioURLRegex = regexp.MustCompile(`^minio://([^/]+)/(.+)$`)

// ResultService provides task result retrieval with presigned URLs.
type ResultService interface {
	GetResult(ctx context.Context, userID uint64, taskUUID string) (*ResultSummary, error)
}

// ResultSummary is the API representation of a task result.
type ResultSummary struct {
	TaskID   string                 `json:"task_id"`
	Status   string                 `json:"status"`
	Files    ResultFiles            `json:"files"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// ResultFiles holds presigned URLs for result files.
type ResultFiles struct {
	TranscriptURL *string `json:"transcript_url,omitempty"`
	SubtitleURL   *string `json:"subtitle_url,omitempty"`
	ParsedURL     *string `json:"parsed_url,omitempty"`
}

// resultService is the concrete ResultService implementation.
type resultService struct {
	logger        *zap.Logger
	taskRepo      repository.TaskRepository
	storage       storage.ObjectStorage
	expiry        time.Duration
	resultsBucket string
}

// NewResultService creates a ResultService.
func NewResultService(logger *zap.Logger, taskRepo repository.TaskRepository, storage storage.ObjectStorage, expiry time.Duration, resultsBucket string) ResultService {
	if logger == nil {
		logger = zap.NewNop()
	}
	return &resultService{
		logger:        logger,
		taskRepo:      taskRepo,
		storage:       storage,
		expiry:        expiry,
		resultsBucket: resultsBucket,
	}
}

// GetResult returns a task result summary with presigned URLs if completed.
func (s *resultService) GetResult(ctx context.Context, userID uint64, taskUUID string) (*ResultSummary, error) {
	task, err := s.taskRepo.GetByUUIDAndUserID(ctx, taskUUID, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.New(404, apperrors.CodeNotFound, "task not found")
		}
		s.logger.Error("failed to get task for result", zap.Error(err))
		return nil, apperrors.Internal("internal server error")
	}

	if task.Status != model.TaskStatusCompleted {
		return nil, apperrors.New(400, apperrors.CodeTaskNotCompleted, "task is not completed")
	}

	files, metadata, err := s.extractFiles(ctx, task.Result)
	if err != nil {
		return nil, err
	}

	return &ResultSummary{
		TaskID:   task.UUID,
		Status:   task.Status,
		Files:    files,
		Metadata: metadata,
	}, nil
}

// extractFiles parses task.result and generates presigned URLs.
func (s *resultService) extractFiles(ctx context.Context, result json.RawMessage) (ResultFiles, map[string]interface{}, error) {
	var files ResultFiles
	metadata := make(map[string]interface{})

	if len(result) == 0 {
		return files, metadata, nil
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(result, &payload); err != nil {
		s.logger.Warn("failed to unmarshal task result", zap.Error(err))
		return files, metadata, nil
	}

	if meta, ok := payload["metadata"].(map[string]interface{}); ok {
		metadata = meta
	}

	files.TranscriptURL = s.presignURL(ctx, payload, "transcript_url")
	files.SubtitleURL = s.presignURL(ctx, payload, "subtitle_url")
	files.ParsedURL = s.presignURL(ctx, payload, "parsed_url")

	return files, metadata, nil
}

// presignURL generates a presigned URL for a minio:// value in the payload.
func (s *resultService) presignURL(ctx context.Context, payload map[string]interface{}, key string) *string {
	raw, ok := payload[key].(string)
	if !ok || raw == "" {
		return nil
	}

	bucket, objectKey, err := parseMinIOURL(raw)
	if err != nil {
		s.logger.Warn("invalid minio url in task result", zap.String("key", key), zap.Error(err))
		return nil
	}

	if bucket != s.resultsBucket {
		s.logger.Warn("result bucket mismatch", zap.String("expected", s.resultsBucket), zap.String("actual", bucket))
		return nil
	}

	presigned, err := s.storage.PresignedGetURL(ctx, objectKey, s.expiry)
	if err != nil {
		s.logger.Error("failed to generate presigned url", zap.String("key", key), zap.Error(err))
		return nil
	}

	return &presigned
}

// parseMinIOURL parses a minio://bucket/object URL.
func parseMinIOURL(raw string) (bucket, objectKey string, err error) {
	if strings.HasPrefix(raw, "minio://") {
		matches := minioURLRegex.FindStringSubmatch(raw)
		if len(matches) == 3 {
			bucket = matches[1]
			objectKey = matches[2]
			return bucket, objectKey, nil
		}
	}

	// Fallback to URL parsing for https/http presigned URLs stored by older workers.
	parsed, err := url.Parse(raw)
	if err != nil {
		return "", "", fmt.Errorf("invalid minio url: %w", err)
	}

	path := strings.TrimPrefix(parsed.Path, "/")
	parts := strings.SplitN(path, "/", 2)
	if len(parts) != 2 {
		return "", "", fmt.Errorf("invalid minio url path: %s", raw)
	}
	return parts[0], parts[1], nil
}
