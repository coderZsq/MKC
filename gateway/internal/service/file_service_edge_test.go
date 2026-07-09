package service

import (
	"context"
	"errors"
	"io"
	"mime/multipart"
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type failingFile struct{}

func (f *failingFile) Read(p []byte) (int, error)    { return 0, errors.New("read failed") }
func (f *failingFile) ReadAt(p []byte, off int64) (int, error) { return 0, errors.New("read failed") }
func (f *failingFile) Close() error                  { return nil }
func (f *failingFile) Seek(offset int64, whence int) (int64, error) {
	return 0, errors.New("seek not supported")
}

var _ multipart.File = (*failingFile)(nil)

func TestMaxFileSize(t *testing.T) {
	assert.Equal(t, int64(500*1024*1024), MaxFileSize())
}

func TestSanitizeFilename(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"hello.txt", "hello.txt"},
		{"/tmp/hello.txt", "hello.txt"},
		{"../secret.txt", "secret.txt"},
		{"", "unnamed"},
		{".", "unnamed"},
		{"/", "unnamed"},
	}

	for _, tc := range tests {
		t.Run(tc.input, func(t *testing.T) {
			assert.Equal(t, tc.want, sanitizeFilename(tc.input))
		})
	}
}

func TestCompatibleMime(t *testing.T) {
	tests := []struct {
		declared string
		detected string
		want     bool
	}{
		{"application/pdf", "application/pdf", true},
		{"application/msword", "application/x-msi", true},
		{"application/msword", "application/octet-stream", true},
		{"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip", true},
		{"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream", true},
		{"audio/mpeg", "audio/x-wav", true},
		{"audio/wav", "audio/x-wav", true},
		{"audio/mp4", "audio/mp4", true},
		{"video/mp4", "video/mp4", true},
		{"video/webm", "video/webm", true},
		{"text/plain", "text/plain", true},
		{"text/plain", "text/html", true},
		{"audio/mpeg", "video/mp4", false},
		{"application/pdf", "application/octet-stream", false},
	}

	for _, tc := range tests {
		t.Run(tc.declared+"_"+tc.detected, func(t *testing.T) {
			assert.Equal(t, tc.want, compatibleMime(tc.declared, tc.detected))
		})
	}
}

func TestFileService_Upload_FileReadError(t *testing.T) {
	svc, _, _, _, _ := newTestFileService(t)

	req := UploadRequest{
		Header: fileHeader("doc.txt", "text/plain", 1),
		File:   &failingFile{},
	}

	_, err := svc.Upload(context.Background(), req)
	require.Error(t, err)

	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusInternalServerError, appErr.Status)
	assert.Equal(t, "INTERNAL_ERROR", appErr.Code)
}

func TestFileService_Upload_StoragePutError(t *testing.T) {
	svc, store, _, _, _ := newTestFileService(t)
	store.putFunc = func(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error {
		return errors.New("put failed")
	}

	req := UploadRequest{
		Header: fileHeader("doc.txt", "text/plain", 5),
		File:   newFakeFile([]byte("hello")),
	}

	_, err := svc.Upload(context.Background(), req)
	require.Error(t, err)

	var appErr *apperrors.AppError
	require.True(t, errors.As(err, &appErr))
	assert.Equal(t, http.StatusInternalServerError, appErr.Status)
	assert.Equal(t, "INTERNAL_ERROR", appErr.Code)
	assert.Empty(t, store.removeKeys)
}

func TestFileService_Upload_MimeCompatibleFallback(t *testing.T) {
	svc, _, resourceRepo, _, _ := newTestFileService(t)
	resourceRepo.createFunc = func(ctx context.Context, r *model.Resource) error {
		r.ID = 1
		return nil
	}

	// Declared .docx but content is a zip signature; compatibleMime accepts it.
	req := UploadRequest{
		Header:   fileHeader("report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 4),
		File:     newFakeFile([]byte("PK\x03\x04")),
		UserID:   1,
		UserUUID: "user-uuid",
	}

	result, err := svc.Upload(context.Background(), req)
	require.NoError(t, err)
	assert.Equal(t, "document_parse", result.Type)
}
