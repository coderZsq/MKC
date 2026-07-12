package service

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"mime/multipart"
	"net/http"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"github.com/zhushuangquan/mkc/gateway/internal/storage"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type fakeFile struct {
	*bytes.Reader
}

func newFakeFile(data []byte) *fakeFile {
	return &fakeFile{Reader: bytes.NewReader(data)}
}

func (f *fakeFile) Close() error { return nil }

var _ multipart.File = (*fakeFile)(nil)

type stubObjectStorage struct {
	putFunc    func(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error
	removeFunc func(ctx context.Context, key string) error
	putCalls   []string
	removeKeys []string
}

func (s *stubObjectStorage) PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error {
	s.putCalls = append(s.putCalls, key)
	if s.putFunc != nil {
		return s.putFunc(ctx, key, reader, size, contentType)
	}
	return nil
}

func (s *stubObjectStorage) RemoveObject(ctx context.Context, key string) error {
	s.removeKeys = append(s.removeKeys, key)
	if s.removeFunc != nil {
		return s.removeFunc(ctx, key)
	}
	return nil
}

func (s *stubObjectStorage) PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	return "", nil
}

var _ storage.ObjectStorage = (*stubObjectStorage)(nil)

type stubResourceRepository struct {
	createFunc              func(ctx context.Context, r *model.Resource) error
	updateStatusFunc        func(ctx context.Context, id uint64, status uint8) error
	getByUUIDAndUserFunc    func(ctx context.Context, uuid string, userID uint64) (*model.Resource, error)
	countByUUIDsAndUserFunc func(ctx context.Context, uuids []string, userID uint64) (int64, error)
}

func (r *stubResourceRepository) Create(ctx context.Context, resource *model.Resource) error {
	if r.createFunc != nil {
		return r.createFunc(ctx, resource)
	}
	return nil
}

func (r *stubResourceRepository) GetByUUID(ctx context.Context, uuid string) (*model.Resource, error) {
	if r.getByUUIDAndUserFunc != nil {
		return r.getByUUIDAndUserFunc(ctx, uuid, 0)
	}
	return nil, repository.ErrNotFound
}

func (r *stubResourceRepository) UpdateStatus(ctx context.Context, id uint64, status uint8) error {
	if r.updateStatusFunc != nil {
		return r.updateStatusFunc(ctx, id, status)
	}
	return nil
}

func (r *stubResourceRepository) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Resource, error) {
	if r.getByUUIDAndUserFunc != nil {
		return r.getByUUIDAndUserFunc(ctx, uuid, userID)
	}
	return nil, repository.ErrNotFound
}

func (r *stubResourceRepository) CountByUUIDsAndUserID(ctx context.Context, uuids []string, userID uint64) (int64, error) {
	if r.countByUUIDsAndUserFunc != nil {
		return r.countByUUIDsAndUserFunc(ctx, uuids, userID)
	}
	return int64(len(uuids)), nil
}

var _ repository.ResourceRepository = (*stubResourceRepository)(nil)

type stubTaskRepository struct {
	createFunc                  func(ctx context.Context, t *model.Task) error
	getByUUIDFunc               func(ctx context.Context, uuid string) (*model.Task, error)
	getByUUIDAndUserID          func(ctx context.Context, uuid string, userID uint64) (*model.Task, error)
	listByUserIDFunc            func(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error)
	updateStatusFunc            func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error
	updateStatusWithAttemptFunc func(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error
	updateProgressFunc          func(ctx context.Context, id uint64, progress uint8) error
	resetForRetryFunc           func(ctx context.Context, id uint64) error
}

func (r *stubTaskRepository) Create(ctx context.Context, task *model.Task) error {
	if r.createFunc != nil {
		return r.createFunc(ctx, task)
	}
	return nil
}

func (r *stubTaskRepository) GetByUUID(ctx context.Context, uuid string) (*model.Task, error) {
	if r.getByUUIDFunc != nil {
		return r.getByUUIDFunc(ctx, uuid)
	}
	return nil, repository.ErrNotFound
}

func (r *stubTaskRepository) GetByUUIDAndUserID(ctx context.Context, uuid string, userID uint64) (*model.Task, error) {
	if r.getByUUIDAndUserID != nil {
		return r.getByUUIDAndUserID(ctx, uuid, userID)
	}
	return nil, repository.ErrNotFound
}

func (r *stubTaskRepository) GetLatestCompletedByResourceID(ctx context.Context, resourceID uint64) (*model.Task, error) {
	return nil, repository.ErrNotFound
}

func (r *stubTaskRepository) ListByUserID(ctx context.Context, userID uint64, page, limit int) ([]model.Task, int64, error) {
	if r.listByUserIDFunc != nil {
		return r.listByUserIDFunc(ctx, userID, page, limit)
	}
	return nil, 0, nil
}

func (r *stubTaskRepository) UpdateStatus(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string) error {
	if r.updateStatusFunc != nil {
		return r.updateStatusFunc(ctx, id, status, progress, result, errMsg)
	}
	return nil
}

func (r *stubTaskRepository) UpdateProgress(ctx context.Context, id uint64, progress uint8) error {
	if r.updateProgressFunc != nil {
		return r.updateProgressFunc(ctx, id, progress)
	}
	return nil
}

func (r *stubTaskRepository) UpdateStatusWithAttempt(ctx context.Context, id uint64, status string, progress uint8, result json.RawMessage, errMsg string, attemptCount uint8) error {
	if r.updateStatusWithAttemptFunc != nil {
		return r.updateStatusWithAttemptFunc(ctx, id, status, progress, result, errMsg, attemptCount)
	}
	return nil
}

func (r *stubTaskRepository) ResetForRetry(ctx context.Context, id uint64) error {
	if r.resetForRetryFunc != nil {
		return r.resetForRetryFunc(ctx, id)
	}
	return nil
}

var _ repository.TaskRepository = (*stubTaskRepository)(nil)

type fakeFileDispatcher struct {
	calls []dispatchCall
}

func (d *fakeFileDispatcher) Dispatch(ctx context.Context, task *model.Task, resource *model.Resource) error {
	d.calls = append(d.calls, dispatchCall{Task: task, Resource: resource})
	return nil
}

func (d *fakeFileDispatcher) DispatchSummary(ctx context.Context, resource *model.Resource, payload SummaryDispatchPayload) error {
	return nil
}

func newTestFileService(t *testing.T) (*fileService, *stubObjectStorage, *stubResourceRepository, *stubTaskRepository, *fakeFileDispatcher) {
	storageStub := &stubObjectStorage{}
	resourceRepo := &stubResourceRepository{}
	taskRepo := &stubTaskRepository{}
	dispatcher := &fakeFileDispatcher{}
	svc := NewFileService(nil, storageStub, resourceRepo, taskRepo, dispatcher).(*fileService)
	return svc, storageStub, resourceRepo, taskRepo, dispatcher
}

func fileHeader(name, contentType string, size int64) *multipart.FileHeader {
	h := &multipart.FileHeader{
		Filename: name,
		Size:     size,
	}
	h.Header = make(map[string][]string)
	h.Header.Set("Content-Type", contentType)
	return h
}

func TestFileService_Upload_MissingFile(t *testing.T) {
	svc, _, _, _, _ := newTestFileService(t)

	_, err := svc.Upload(context.Background(), UploadRequest{})

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusBadRequest, appErr.Status)
	assert.Equal(t, "FILE_MISSING", appErr.Code)
}

func TestFileService_Upload_TooLarge(t *testing.T) {
	svc, _, _, _, _ := newTestFileService(t)

	req := UploadRequest{
		Header: fileHeader("big.mp4", "video/mp4", MaxFileSizeBytes+1),
		File:   newFakeFile([]byte("x")),
	}

	_, err := svc.Upload(context.Background(), req)

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusRequestEntityTooLarge, appErr.Status)
	assert.Equal(t, "FILE_TOO_LARGE", appErr.Code)
}

func TestFileService_Upload_UnsupportedType(t *testing.T) {
	svc, _, _, _, _ := newTestFileService(t)

	req := UploadRequest{
		Header: fileHeader("bad.exe", "application/x-msdownload", 4),
		File:   newFakeFile([]byte{0x4d, 0x5a, 0x00, 0x00}),
	}

	_, err := svc.Upload(context.Background(), req)

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusUnsupportedMediaType, appErr.Status)
	assert.Equal(t, "FILE_UNSUPPORTED_TYPE", appErr.Code)
}

func TestFileService_Upload_MimeMismatch(t *testing.T) {
	svc, _, _, _, _ := newTestFileService(t)

	req := UploadRequest{
		Header: fileHeader("fake.txt", "text/plain", 8),
		File:   newFakeFile([]byte{0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a}),
	}

	_, err := svc.Upload(context.Background(), req)

	require.Error(t, err)
	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusUnsupportedMediaType, appErr.Status)
	assert.Equal(t, "FILE_UNSUPPORTED_TYPE", appErr.Code)
}

func TestFileService_Upload_Success_MP3_AudioMp3(t *testing.T) {
	svc, store, resourceRepo, _, _ := newTestFileService(t)

	userUUID := uuid.NewString()
	resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
		r.ID = 1
		return nil
	}

	req := UploadRequest{
		Header:   fileHeader("song.mp3", "audio/mp3", 10),
		File:     newFakeFile([]byte{0xff, 0xfb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}),
		UserID:   42,
		UserUUID: userUUID,
	}

	result, err := svc.Upload(context.Background(), req)

	require.NoError(t, err)
	assert.Equal(t, "audio/mp3", result.MimeType)
	assert.Equal(t, "media_parse", result.Type)
	assert.Len(t, store.putCalls, 1)
}

func TestFileService_Upload_Success(t *testing.T) {
	svc, store, resourceRepo, _, _ := newTestFileService(t)

	userUUID := uuid.NewString()
	resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
		r.ID = 1
		return nil
	}

	req := UploadRequest{
		Header:   fileHeader("song.mp3", "audio/mpeg", 10),
		File:     newFakeFile([]byte{0xff, 0xfb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}),
		UserID:   42,
		UserUUID: userUUID,
	}

	result, err := svc.Upload(context.Background(), req)

	require.NoError(t, err)
	assert.NotEmpty(t, result.ResourceID)
	assert.NotEmpty(t, result.TaskID)
	assert.Equal(t, "song.mp3", result.Name)
	assert.Equal(t, "media_parse", result.Type)
	assert.Equal(t, "uploading", result.Status)
	assert.Equal(t, int64(10), result.SizeBytes)
	assert.Equal(t, "audio/mpeg", result.MimeType)
	assert.Len(t, store.putCalls, 1)
	assert.Contains(t, store.putCalls[0], userUUID)
	assert.Empty(t, store.removeKeys)
}

func TestFileService_Upload_TaskTypeMapping(t *testing.T) {
	tests := []struct {
		mime     string
		data     []byte
		wantType string
	}{
		{"audio/mpeg", []byte{0xff, 0xfb, 0x00, 0x00}, "media_parse"},
		{"audio/mp3", []byte{0xff, 0xfb, 0x00, 0x00}, "media_parse"},
		{"video/mp4", []byte("\x00\x00\x00\x18ftypmp4"), "media_parse"},
		{"application/pdf", []byte("%PDF-1.4"), "pdf_parse"},
		{"text/plain", []byte("hello"), "document_parse"},
		{"application/vnd.openxmlformats-officedocument.wordprocessingml.document", []byte("PK\x03\x04"), "document_parse"},
	}

	for _, tc := range tests {
		t.Run(tc.mime, func(t *testing.T) {
			svc, _, resourceRepo, _, _ := newTestFileService(t)
			resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
				r.ID = 1
				return nil
			}

			req := UploadRequest{
				Header:   fileHeader("doc", tc.mime, int64(len(tc.data))),
				File:     newFakeFile(tc.data),
				UserID:   1,
				UserUUID: uuid.NewString(),
			}

			result, err := svc.Upload(context.Background(), req)
			require.NoError(t, err)
			assert.Equal(t, tc.wantType, result.Type)
		})
	}
}

func TestFileService_Upload_ResourceRepoError_RollbacksObject(t *testing.T) {
	svc, store, resourceRepo, _, _ := newTestFileService(t)

	resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
		return errors.New("db error")
	}

	req := UploadRequest{
		Header:   fileHeader("song.mp3", "audio/mpeg", 5),
		File:     newFakeFile([]byte{0xff, 0xfb, 0x00, 0x00, 0x00}),
		UserID:   1,
		UserUUID: uuid.NewString(),
	}

	_, err := svc.Upload(context.Background(), req)

	require.Error(t, err)
	assert.Len(t, store.putCalls, 1)
	assert.Len(t, store.removeKeys, 1)
	assert.Equal(t, store.putCalls[0], store.removeKeys[0])
}

func TestFileService_Upload_TaskRepoError_RollbacksObject(t *testing.T) {
	svc, store, resourceRepo, taskRepo, _ := newTestFileService(t)

	resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
		r.ID = 1
		return nil
	}
	taskRepo.createFunc = func(ctx context.Context, task *model.Task) error {
		return errors.New("db error")
	}

	req := UploadRequest{
		Header:   fileHeader("song.mp3", "audio/mpeg", 5),
		File:     newFakeFile([]byte{0xff, 0xfb, 0x00, 0x00, 0x00}),
		UserID:   1,
		UserUUID: uuid.NewString(),
	}

	_, err := svc.Upload(context.Background(), req)

	require.Error(t, err)
	assert.Len(t, store.putCalls, 1)
	assert.Len(t, store.removeKeys, 1)
	assert.Equal(t, store.putCalls[0], store.removeKeys[0])
}

func TestFileService_Upload_DispatchesAutoTasks(t *testing.T) {
	svc, _, resourceRepo, _, dispatcher := newTestFileService(t)
	resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
		r.ID = 1
		return nil
	}

	req := UploadRequest{
		Header:   fileHeader("song.mp3", "audio/mpeg", 10),
		File:     newFakeFile([]byte{0xff, 0xfb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}),
		UserID:   1,
		UserUUID: "user-uuid",
	}

	_, err := svc.Upload(context.Background(), req)

	require.NoError(t, err)
	require.Len(t, dispatcher.calls, 1)
	assert.Equal(t, model.TaskTypeMediaParse, dispatcher.calls[0].Task.Type)
}

func TestFileService_Upload_DispatchFailureMarksTaskFailed(t *testing.T) {
	svc, _, resourceRepo, taskRepo, _ := newTestFileService(t)
	resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
		r.ID = 1
		return nil
	}
	taskRepo.createFunc = func(ctx context.Context, t *model.Task) error {
		t.ID = 2
		return nil
	}
	var status string
	var errMsg string
	taskRepo.updateStatusFunc = func(ctx context.Context, id uint64, s string, progress uint8, result json.RawMessage, msg string) error {
		status = s
		errMsg = msg
		return nil
	}
	svc.dispatcher = &alwaysFailingDispatcher{}

	req := UploadRequest{
		Header:   fileHeader("doc.pdf", "application/pdf", 8),
		File:     newFakeFile([]byte("%PDF-1.4")),
		UserID:   1,
		UserUUID: "user-uuid",
	}

	_, err := svc.Upload(context.Background(), req)

	require.NoError(t, err)
	assert.Equal(t, model.TaskStatusFailed, status)
	assert.Contains(t, errMsg, "dispatch failed")
}

type alwaysFailingDispatcher struct{}

func (d *alwaysFailingDispatcher) Dispatch(ctx context.Context, task *model.Task, resource *model.Resource) error {
	return errors.New("dispatch failed")
}

func (d *alwaysFailingDispatcher) DispatchSummary(ctx context.Context, resource *model.Resource, payload SummaryDispatchPayload) error {
	return errors.New("dispatch failed")
}
