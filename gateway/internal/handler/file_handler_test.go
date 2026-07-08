package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type stubFileService struct {
	uploadFunc func(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error)
}

func (s *stubFileService) Upload(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error) {
	if s.uploadFunc != nil {
		return s.uploadFunc(ctx, req)
	}
	return nil, nil
}

var _ service.FileService = (*stubFileService)(nil)

func buildUploadRequest(t *testing.T, fieldName, filename, contentType string, body []byte, contentLength int64) (*httptest.ResponseRecorder, *gin.Context) {
	t.Helper()
	gin.SetMode(gin.TestMode)

	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)
	part, err := writer.CreateFormFile(fieldName, filename)
	require.NoError(t, err)
	_, err = part.Write(body)
	require.NoError(t, err)
	require.NoError(t, writer.Close())

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/files/upload", &buf)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	if contentLength > 0 {
		req.ContentLength = contentLength
	}
	c.Request = req
	c.Set("user_uuid", "user-uuid")
	c.Set("user_id", uint64(42))
	return w, c
}

func TestFileHandler_Upload_Success(t *testing.T) {
	svc := &stubFileService{
		uploadFunc: func(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error) {
			assert.Equal(t, uint64(42), req.UserID)
			assert.Equal(t, "user-uuid", req.UserUUID)
			assert.Equal(t, "hello.txt", req.Header.Filename)
			return &service.UploadResult{
				ResourceID: "resource-uuid",
				TaskID:     "task-uuid",
				Name:       "hello.txt",
				Type:       "document_parse",
				Status:     "uploading",
				SizeBytes:  5,
				MimeType:   "text/plain",
			}, nil
		},
	}
	h := NewFileHandler(svc)

	w, c := buildUploadRequest(t, "file", "hello.txt", "text/plain", []byte("hello"), 0)
	h.Upload(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "resource-uuid", data["resource_id"])
	assert.Equal(t, "task-uuid", data["task_id"])
}

func TestFileHandler_Upload_MissingFile(t *testing.T) {
	svc := &stubFileService{}
	h := NewFileHandler(svc)

	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	require.NoError(t, writer.Close())
	req := httptest.NewRequest(http.MethodPost, "/api/v1/files/upload", body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	c.Request = req
	c.Set("user_uuid", "user-uuid")
	c.Set("user_id", uint64(42))

	h.Upload(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, "FILE_MISSING", errInfo["code"])
}

func TestFileHandler_Upload_ContentLengthTooLarge(t *testing.T) {
	svc := &stubFileService{
		uploadFunc: func(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error) {
			t.Fatal("service should not be called")
			return nil, nil
		},
	}
	h := NewFileHandler(svc)

	w, c := buildUploadRequest(t, "file", "big.bin", "application/octet-stream", []byte("x"), service.MaxFileSize()+1)
	h.Upload(c)

	assert.Equal(t, http.StatusRequestEntityTooLarge, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.False(t, resp["success"].(bool))
	errInfo := resp["error"].(map[string]any)
	assert.Equal(t, "FILE_TOO_LARGE", errInfo["code"])
}

func TestFileHandler_Upload_FileTooLargeFromService(t *testing.T) {
	svc := &stubFileService{
		uploadFunc: func(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error) {
			return nil, apperrors.FileTooLarge("too big")
		},
	}
	h := NewFileHandler(svc)

	w, c := buildUploadRequest(t, "file", "big.bin", "application/octet-stream", []byte("x"), 0)
	h.Upload(c)

	assert.Equal(t, http.StatusRequestEntityTooLarge, w.Code)
}

func TestFileHandler_Upload_UnsupportedMediaType(t *testing.T) {
	svc := &stubFileService{
		uploadFunc: func(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error) {
			return nil, apperrors.UnsupportedMediaType("bad type")
		},
	}
	h := NewFileHandler(svc)

	w, c := buildUploadRequest(t, "file", "bad.bin", "application/octet-stream", []byte("x"), 0)
	h.Upload(c)

	assert.Equal(t, http.StatusUnsupportedMediaType, w.Code)
}

func TestFileHandler_Upload_InternalError(t *testing.T) {
	svc := &stubFileService{
		uploadFunc: func(ctx context.Context, req service.UploadRequest) (*service.UploadResult, error) {
			return nil, errors.New("unexpected")
		},
	}
	h := NewFileHandler(svc)

	w, c := buildUploadRequest(t, "file", "hello.txt", "text/plain", []byte("hello"), 0)
	h.Upload(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
}
