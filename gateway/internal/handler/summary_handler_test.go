package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
)

type stubSummaryService struct {
	saveFunc func(ctx context.Context, resourceUUID string, req service.SaveSummaryRequest) error
	getFunc  func(ctx context.Context, userID uint64, resourceUUID string) (*service.ResourceSummary, error)
}

func (s *stubSummaryService) SaveInternal(ctx context.Context, resourceUUID string, req service.SaveSummaryRequest) error {
	if s.saveFunc != nil {
		return s.saveFunc(ctx, resourceUUID, req)
	}
	return nil
}

func (s *stubSummaryService) GetByResource(ctx context.Context, userID uint64, resourceUUID string) (*service.ResourceSummary, error) {
	if s.getFunc != nil {
		return s.getFunc(ctx, userID, resourceUUID)
	}
	return nil, nil
}

func (s *stubSummaryService) Trigger(ctx context.Context, userID uint64, resourceUUID string) (*service.TriggerSummaryResult, error) {
	return &service.TriggerSummaryResult{ResourceID: resourceUUID, TaskID: "sum-" + resourceUUID, Status: "pending"}, nil
}

func TestSummaryHandler_SaveInternal(t *testing.T) {
	svc := &stubSummaryService{
		saveFunc: func(ctx context.Context, resourceUUID string, req service.SaveSummaryRequest) error {
			assert.Equal(t, "res-1", resourceUUID)
			assert.Equal(t, "全文", req.FullSummary)
			return nil
		},
	}
	h := NewSummaryHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/internal/resources/res-1/summaries", bytes.NewBufferString(`{"full_summary":"全文","model":"mock"}`))
	c.Params = append(c.Params, ginParam("id", "res-1"))
	c.Request.Header.Set("Content-Type", "application/json")

	h.SaveInternal(c)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestSummaryHandler_Get(t *testing.T) {
	svc := &stubSummaryService{
		getFunc: func(ctx context.Context, userID uint64, resourceUUID string) (*service.ResourceSummary, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, "res-1", resourceUUID)
			return &service.ResourceSummary{ResourceID: "res-1", FullSummary: "全文"}, nil
		},
	}
	h := NewSummaryHandler(svc)
	w, c := newTaskHandlerTestContext(t, http.MethodGet, "/api/v1/resources/res-1/summary", nil)
	c.Params = append(c.Params, ginParam("id", "res-1"))

	h.Get(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "全文", data["full_summary"])
}

func TestSummaryHandler_Trigger(t *testing.T) {
	h := NewSummaryHandler(&stubSummaryService{})
	w, c := newTaskHandlerTestContext(t, http.MethodPost, "/api/v1/resources/res-1/summary", nil)
	c.Params = append(c.Params, ginParam("id", "res-1"))

	h.Trigger(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "pending", data["status"])
}

func ginParam(key string, value string) gin.Param {
	return gin.Param{Key: key, Value: value}
}
