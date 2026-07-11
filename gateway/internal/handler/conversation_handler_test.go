package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type stubConversationService struct {
	createFunc        func(ctx context.Context, userID uint64, req service.CreateConversationRequest) (*service.ConversationResponse, error)
	listFunc          func(ctx context.Context, userID uint64, page, limit int) ([]service.ConversationResponse, int64, error)
	getFunc           func(ctx context.Context, userID uint64, id string) (*service.ConversationResponse, error)
	deleteFunc        func(ctx context.Context, userID uint64, id string) error
	listMessagesFunc  func(ctx context.Context, userID uint64, conversationID string, page, limit int) (*service.MessageListResponse, error)
	createMessageFunc func(ctx context.Context, userID uint64, conversationID string, req service.CreateMessageRequest) (*service.MessageResponse, error)
}

func (s *stubConversationService) Create(ctx context.Context, userID uint64, req service.CreateConversationRequest) (*service.ConversationResponse, error) {
	if s.createFunc != nil {
		return s.createFunc(ctx, userID, req)
	}
	return nil, nil
}

func (s *stubConversationService) List(ctx context.Context, userID uint64, page, limit int) ([]service.ConversationResponse, int64, error) {
	if s.listFunc != nil {
		return s.listFunc(ctx, userID, page, limit)
	}
	return nil, 0, nil
}

func (s *stubConversationService) Get(ctx context.Context, userID uint64, id string) (*service.ConversationResponse, error) {
	if s.getFunc != nil {
		return s.getFunc(ctx, userID, id)
	}
	return nil, nil
}

func (s *stubConversationService) Delete(ctx context.Context, userID uint64, id string) error {
	if s.deleteFunc != nil {
		return s.deleteFunc(ctx, userID, id)
	}
	return nil
}

func (s *stubConversationService) ListMessages(ctx context.Context, userID uint64, conversationID string, page, limit int) (*service.MessageListResponse, error) {
	if s.listMessagesFunc != nil {
		return s.listMessagesFunc(ctx, userID, conversationID, page, limit)
	}
	return nil, nil
}

func (s *stubConversationService) CreateMessage(ctx context.Context, userID uint64, conversationID string, req service.CreateMessageRequest) (*service.MessageResponse, error) {
	if s.createMessageFunc != nil {
		return s.createMessageFunc(ctx, userID, conversationID, req)
	}
	return nil, nil
}

func newConversationHandlerTestContext(method, path string, body []byte) (*gin.Context, *httptest.ResponseRecorder) {
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(method, path, bytes.NewReader(body))
	c.Request.Header.Set("Content-Type", "application/json")
	c.Set("user_id", uint64(1))
	return c, w
}

func TestConversationHandler_CreateConversation(t *testing.T) {
	svc := &stubConversationService{
		createFunc: func(ctx context.Context, userID uint64, req service.CreateConversationRequest) (*service.ConversationResponse, error) {
			return &service.ConversationResponse{ID: "conv-1", Title: req.Title}, nil
		},
	}
	h := NewConversationHandler(svc)

	body, _ := json.Marshal(map[string]any{"title": "project", "resource_ids": []string{"res-1"}})
	c, w := newConversationHandlerTestContext(http.MethodPost, "/api/v1/conversations", body)
	h.CreateConversation(c)

	assert.Equal(t, http.StatusCreated, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	data := resp["data"].(map[string]any)
	assert.Equal(t, "conv-1", data["id"])
}

func TestConversationHandler_CreateConversation_EmptyBody(t *testing.T) {
	svc := &stubConversationService{
		createFunc: func(ctx context.Context, userID uint64, req service.CreateConversationRequest) (*service.ConversationResponse, error) {
			assert.Empty(t, req.Title)
			assert.Empty(t, req.ResourceIDs)
			return &service.ConversationResponse{ID: "conv-1", Title: "新会话"}, nil
		},
	}
	h := NewConversationHandler(svc)

	c, w := newConversationHandlerTestContext(http.MethodPost, "/api/v1/conversations", nil)
	h.CreateConversation(c)

	assert.Equal(t, http.StatusCreated, w.Code)
}

func TestConversationHandler_CreateConversation_ValidationError(t *testing.T) {
	h := NewConversationHandler(&stubConversationService{})
	c, w := newConversationHandlerTestContext(http.MethodPost, "/api/v1/conversations", []byte(`{`))
	h.CreateConversation(c)
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestConversationHandler_ListConversations(t *testing.T) {
	svc := &stubConversationService{
		listFunc: func(ctx context.Context, userID uint64, page, limit int) ([]service.ConversationResponse, int64, error) {
			return []service.ConversationResponse{{ID: "conv-1", Title: "t"}}, 1, nil
		},
	}
	h := NewConversationHandler(svc)
	c, w := newConversationHandlerTestContext(http.MethodGet, "/api/v1/conversations?page=1&limit=10", nil)
	h.ListConversations(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
	meta := resp["meta"].(map[string]any)
	assert.Equal(t, float64(1), meta["total"])
}

func TestConversationHandler_GetConversation(t *testing.T) {
	svc := &stubConversationService{
		getFunc: func(ctx context.Context, userID uint64, id string) (*service.ConversationResponse, error) {
			if id == "conv-1" {
				return &service.ConversationResponse{ID: id, Title: "t"}, nil
			}
			return nil, apperrors.NotFound("conversation")
		},
	}
	h := NewConversationHandler(svc)

	c, w := newConversationHandlerTestContext(http.MethodGet, "/api/v1/conversations/conv-1", nil)
	c.Params = gin.Params{{Key: "id", Value: "conv-1"}}
	h.GetConversation(c)
	assert.Equal(t, http.StatusOK, w.Code)

	c2, w2 := newConversationHandlerTestContext(http.MethodGet, "/api/v1/conversations/missing", nil)
	c2.Params = gin.Params{{Key: "id", Value: "missing"}}
	h.GetConversation(c2)
	assert.Equal(t, http.StatusNotFound, w2.Code)
}

func TestConversationHandler_DeleteConversation(t *testing.T) {
	svc := &stubConversationService{
		deleteFunc: func(ctx context.Context, userID uint64, id string) error {
			return nil
		},
	}
	h := NewConversationHandler(svc)
	c, w := newConversationHandlerTestContext(http.MethodDelete, "/api/v1/conversations/conv-1", nil)
	c.Params = gin.Params{{Key: "id", Value: "conv-1"}}
	h.DeleteConversation(c)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestConversationHandler_ListMessages(t *testing.T) {
	svc := &stubConversationService{
		listMessagesFunc: func(ctx context.Context, userID uint64, conversationID string, page, limit int) (*service.MessageListResponse, error) {
			return &service.MessageListResponse{
				Items: []service.MessageResponse{{ID: "msg-1", Role: "user", Content: "hello"}},
				Total: 1,
				Page:  page,
				Limit: limit,
			}, nil
		},
	}
	h := NewConversationHandler(svc)
	c, w := newConversationHandlerTestContext(http.MethodGet, "/api/v1/conversations/conv-1/messages?page=1&limit=10", nil)
	c.Params = gin.Params{{Key: "id", Value: "conv-1"}}
	h.ListMessages(c)

	assert.Equal(t, http.StatusOK, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	data := resp["data"].(map[string]any)
	items := data["items"].([]any)
	assert.Len(t, items, 1)
}

func TestConversationHandler_ListMessages_InvalidPagination(t *testing.T) {
	h := NewConversationHandler(&stubConversationService{})
	c, w := newConversationHandlerTestContext(http.MethodGet, "/api/v1/conversations/conv-1/messages?page=0", nil)
	c.Params = gin.Params{{Key: "id", Value: "conv-1"}}
	h.ListMessages(c)
	assert.Equal(t, http.StatusBadRequest, w.Code)

	c2, w2 := newConversationHandlerTestContext(http.MethodGet, "/api/v1/conversations/conv-1/messages?limit=0", nil)
	c2.Params = gin.Params{{Key: "id", Value: "conv-1"}}
	h.ListMessages(c2)
	assert.Equal(t, http.StatusBadRequest, w2.Code)
}

func TestConversationHandler_CreateMessage(t *testing.T) {
	svc := &stubConversationService{
		createMessageFunc: func(ctx context.Context, userID uint64, conversationID string, req service.CreateMessageRequest) (*service.MessageResponse, error) {
			return &service.MessageResponse{ID: "msg-1", Role: req.Role, Content: req.Content}, nil
		},
	}
	h := NewConversationHandler(svc)
	body, _ := json.Marshal(map[string]any{"role": "user", "content": "hello"})
	c, w := newConversationHandlerTestContext(http.MethodPost, "/api/v1/conversations/conv-1/messages", body)
	c.Params = gin.Params{{Key: "id", Value: "conv-1"}}
	h.CreateMessage(c)

	assert.Equal(t, http.StatusCreated, w.Code)
	var resp map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	assert.True(t, resp["success"].(bool))
}
