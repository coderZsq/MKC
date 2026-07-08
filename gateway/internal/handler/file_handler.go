package handler

import (
	"errors"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
)

// FileHandler exposes file upload endpoints.
type FileHandler struct {
	svc service.FileService
}

// NewFileHandler creates a FileHandler.
func NewFileHandler(svc service.FileService) *FileHandler {
	return &FileHandler{svc: svc}
}

// Upload handles single file upload requests.
func (h *FileHandler) Upload(c *gin.Context) {
	userUUID := c.GetString("user_uuid")
	userID := c.GetUint64("user_id")

	if c.Request.ContentLength > service.MaxFileSize() {
		response.Error(c, http.StatusRequestEntityTooLarge, "FILE_TOO_LARGE", "file exceeds 500MB limit")
		return
	}

	file, header, err := c.Request.FormFile("file")
	if err != nil {
		if errors.Is(err, http.ErrMissingFile) || strings.Contains(err.Error(), "missing") {
			response.BadRequest(c, "FILE_MISSING", "missing file field")
			return
		}
		response.BadRequest(c, "FILE_MISSING", "invalid file field")
		return
	}
	defer file.Close()

	result, err := h.svc.Upload(c.Request.Context(), service.UploadRequest{
		File:     file,
		Header:   header,
		UserID:   userID,
		UserUUID: userUUID,
	})
	if err != nil {
		mapFileError(c, err)
		return
	}

	response.OK(c, result)
}

func mapFileError(c *gin.Context, err error) {
	var appErr *apperrors.AppError
	if errors.As(err, &appErr) {
		response.Error(c, appErr.Status, appErr.Code, appErr.Message)
		return
	}
	response.InternalError(c)
}
