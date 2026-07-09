package service

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"path"
	"strings"

	"github.com/google/uuid"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"github.com/zhushuangquan/mkc/gateway/internal/storage"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

const (
	MaxFileSizeBytes = 500 * 1024 * 1024 // 500 MB
	maxMimeSniffLen  = 512
)

// MaxFileSize returns the maximum allowed upload size in bytes.
func MaxFileSize() int64 {
	return MaxFileSizeBytes
}

var allowedMimeTypes = map[string]bool{
	"audio/mpeg":  true,
	"audio/wav":   true,
	"audio/mp4":   true,
	"video/mp4":   true,
	"video/webm":  true,
	"application/pdf": true,
	"text/plain":  true,
	"application/msword": true,
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
}

// UploadRequest carries a multipart file and its owner.
type UploadRequest struct {
	File     multipart.File
	Header   *multipart.FileHeader
	UserID   uint64
	UserUUID string
}

// UploadResult is returned after a successful upload.
type UploadResult struct {
	ResourceID string    `json:"resource_id"`
	TaskID     string    `json:"task_id"`
	Name       string    `json:"name"`
	Type       string    `json:"type"`
	Status     string    `json:"status"`
	SizeBytes  int64     `json:"size_bytes"`
	MimeType   string    `json:"mime_type"`
	CreatedAt  int64     `json:"created_at"`
}

// FileService defines file upload operations.
type FileService interface {
	Upload(ctx context.Context, req UploadRequest) (*UploadResult, error)
}

// fileService is the concrete FileService implementation.
type fileService struct {
	logger       *zap.Logger
	storage      storage.ObjectStorage
	resourceRepo repository.ResourceRepository
	taskRepo     repository.TaskRepository
	dispatcher   TaskDispatcher
}

// NewFileService creates a FileService.
func NewFileService(logger *zap.Logger, storage storage.ObjectStorage, resourceRepo repository.ResourceRepository, taskRepo repository.TaskRepository, dispatcher TaskDispatcher) FileService {
	if logger == nil {
		logger = zap.NewNop()
	}
	return &fileService{
		logger:       logger,
		storage:      storage,
		resourceRepo: resourceRepo,
		taskRepo:     taskRepo,
		dispatcher:   dispatcher,
	}
}

// Upload validates and stores the file, creates resource and task records, and dispatches parse tasks.
func (s *fileService) Upload(ctx context.Context, req UploadRequest) (*UploadResult, error) {
	if req.Header == nil {
		return nil, apperrors.New(http.StatusBadRequest, "FILE_MISSING", "missing file")
	}

	if req.Header.Size > MaxFileSizeBytes {
		return nil, apperrors.FileTooLarge("file exceeds 500MB limit")
	}

	declaredMime := req.Header.Header.Get("Content-Type")
	if !allowedMimeTypes[declaredMime] {
		return nil, apperrors.UnsupportedMediaType("unsupported file type")
	}

	// Peek first bytes to detect actual MIME type without consuming the reader.
	buf := make([]byte, maxMimeSniffLen)
	n, err := req.File.Read(buf)
	if err != nil && err != io.EOF {
		return nil, apperrors.Internal(fmt.Sprintf("failed to read file header: %v", err))
	}
	buf = buf[:n]

	detected := http.DetectContentType(buf)
	if !strings.HasPrefix(detected, declaredMime) && !compatibleMime(declaredMime, detected) {
		return nil, apperrors.UnsupportedMediaType("file content does not match declared type")
	}

	resourceUUID := uuid.NewString()
	key := fmt.Sprintf("%s/%s/%s", req.UserUUID, resourceUUID, sanitizeFilename(req.Header.Filename))

	reader := io.MultiReader(bytes.NewReader(buf), req.File)
	if err := s.storage.PutObject(ctx, key, reader, req.Header.Size, declaredMime); err != nil {
		return nil, apperrors.Internal("failed to upload file")
	}

	resource := &model.Resource{
		UUID:       resourceUUID,
		UserID:     req.UserID,
		Name:       req.Header.Filename,
		Type:       detectTaskType(declaredMime),
		Status:     1, // uploading
		StorageKey: key,
		SizeBytes:  req.Header.Size,
		MimeType:   declaredMime,
	}

	if err := s.resourceRepo.Create(ctx, resource); err != nil {
		_ = s.storage.RemoveObject(ctx, key)
		return nil, apperrors.Internal("failed to save resource")
	}

	task := &model.Task{
		UUID:       uuid.NewString(),
		ResourceID: resource.ID,
		UserID:     req.UserID,
		Type:       resource.Type,
		Status:     model.TaskStatusPending,
	}

	if err := s.taskRepo.Create(ctx, task); err != nil {
		_ = s.storage.RemoveObject(ctx, key)
		return nil, apperrors.Internal("failed to create parse task")
	}

	if s.dispatcher != nil && isAutoDispatchType(resource.Type) {
		if dispatchErr := s.dispatcher.Dispatch(ctx, task, resource); dispatchErr != nil {
			s.logger.Warn("failed to dispatch upload task",
				zap.String("task_id", task.UUID),
				zap.String("resource_id", resource.UUID),
				zap.Error(dispatchErr),
			)
		}
	}

	return &UploadResult{
		ResourceID: resource.UUID,
		TaskID:     task.UUID,
		Name:       resource.Name,
		Type:       resource.Type,
		Status:     "uploading",
		SizeBytes:  resource.SizeBytes,
		MimeType:   resource.MimeType,
		CreatedAt:  resource.CreatedAt.Unix(),
	}, nil
}

func isAutoDispatchType(taskType string) bool {
	return taskType == model.TaskTypeMediaParse || taskType == model.TaskTypePdfParse
}

func detectTaskType(mime string) string {
	if strings.HasPrefix(mime, "audio/") || strings.HasPrefix(mime, "video/") {
		return model.TaskTypeMediaParse
	}
	if mime == "application/pdf" {
		return model.TaskTypePdfParse
	}
	return model.TaskTypeDocumentParse
}

func sanitizeFilename(name string) string {
	name = path.Base(name)
	name = strings.ReplaceAll(name, "..", "_")
	if name == "" || name == "." || name == "/" {
		name = "unnamed"
	}
	return name
}

// compatibleMime returns true when detected MIME is compatible with declared MIME.
func compatibleMime(declared, detected string) bool {
	// Some detectors return generic types for specific declared types.
	switch declared {
	case "application/pdf":
		return detected == "application/pdf"
	case "application/msword":
		return detected == "application/x-msi" || detected == "application/octet-stream"
	case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
		return detected == "application/zip" || detected == "application/octet-stream"
	case "audio/mpeg", "audio/mp4", "audio/wav":
		return strings.HasPrefix(detected, "audio/") || detected == "application/octet-stream"
	case "video/mp4", "video/webm":
		return strings.HasPrefix(detected, "video/") || detected == "application/octet-stream"
	case "text/plain":
		return strings.HasPrefix(detected, "text/")
	}
	return false
}
