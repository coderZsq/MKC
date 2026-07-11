package handler

import (
	"bytes"
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type stubQAService struct {
	askFunc func(ctx context.Context, userID uint64, userUUID string, conversationUUID string, question string) (<-chan service.SSEEvent, error)
}

func (s *stubQAService) Ask(ctx context.Context, userID uint64, userUUID string, conversationUUID string, question string) (<-chan service.SSEEvent, error) {
	if s.askFunc != nil {
		return s.askFunc(ctx, userID, userUUID, conversationUUID, question)
	}
	return nil, nil
}

var _ service.QAService = (*stubQAService)(nil)

func newQASSETestContext(t *testing.T, method, path string, body *bytes.Buffer) (*httptest.ResponseRecorder, *gin.Context) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	if body == nil {
		body = &bytes.Buffer{}
	}
	c.Request = httptest.NewRequest(method, path, body)
	c.Set("user_id", uint64(42))
	c.Set("user_uuid", "user-uuid")
	return w, c
}

func TestQASSEHandler_Ask_Success(t *testing.T) {
	svc := &stubQAService{
		askFunc: func(ctx context.Context, userID uint64, userUUID string, conversationUUID string, question string) (<-chan service.SSEEvent, error) {
			assert.Equal(t, uint64(42), userID)
			assert.Equal(t, "user-uuid", userUUID)
			assert.Equal(t, "conv-1", conversationUUID)
			assert.Equal(t, "hello?", question)

			ch := make(chan service.SSEEvent, 2)
			ch <- service.SSEEvent{Event: "chunk", Data: []byte(`{"delta":"hi"}`), Raw: "event: chunk\ndata: {\"delta\":\"hi\"}\n\n"}
			ch <- service.SSEEvent{Event: "done", Data: []byte(`{"finish_reason":"stop"}`), Raw: "event: done\ndata: {\"finish_reason\":\"stop\"}\n\n"}
			close(ch)
			return ch, nil
		},
	}

	body := bytes.NewBufferString(`{"question":"hello?"}`)
	w, c := newQASSETestContext(t, http.MethodPost, "/api/v1/conversations/conv-1/ask", body)
	c.Params = []gin.Param{{Key: "id", Value: "conv-1"}}
	c.Request.Header.Set("Content-Type", "application/json")

	h := NewQASSEHandler(svc)
	h.Ask(c)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "text/event-stream; charset=utf-8", w.Header().Get("Content-Type"))
	assert.Contains(t, w.Body.String(), "event: chunk")
	assert.Contains(t, w.Body.String(), "event: done")
}

func TestQASSEHandler_Ask_ConversationNotFound(t *testing.T) {
	svc := &stubQAService{
		askFunc: func(ctx context.Context, userID uint64, userUUID string, conversationUUID string, question string) (<-chan service.SSEEvent, error) {
			return nil, apperrors.New(http.StatusNotFound, "CONVERSATION_NOT_FOUND", "会话不存在")
		},
	}

	body := bytes.NewBufferString(`{"question":"hello?"}`)
	w, c := newQASSETestContext(t, http.MethodPost, "/api/v1/conversations/conv-1/ask", body)
	c.Params = []gin.Param{{Key: "id", Value: "conv-1"}}
	c.Request.Header.Set("Content-Type", "application/json")

	h := NewQASSEHandler(svc)
	h.Ask(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
	assert.Contains(t, w.Body.String(), "CONVERSATION_NOT_FOUND")
}

func TestQASSEHandler_Ask_InvalidBody(t *testing.T) {
	svc := &stubQAService{}

	body := bytes.NewBufferString(`{}`)
	w, c := newQASSETestContext(t, http.MethodPost, "/api/v1/conversations/conv-1/ask", body)
	c.Params = []gin.Param{{Key: "id", Value: "conv-1"}}
	c.Request.Header.Set("Content-Type", "application/json")

	h := NewQASSEHandler(svc)
	h.Ask(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	assert.Contains(t, w.Body.String(), "VALIDATION_ERROR")
}

func TestQASSEHandler_Ask_InternalError(t *testing.T) {
	svc := &stubQAService{
		askFunc: func(ctx context.Context, userID uint64, userUUID string, conversationUUID string, question string) (<-chan service.SSEEvent, error) {
			return nil, errors.New("boom")
		},
	}

	body := bytes.NewBufferString(`{"question":"hello?"}`)
	w, c := newQASSETestContext(t, http.MethodPost, "/api/v1/conversations/conv-1/ask", body)
	c.Params = []gin.Param{{Key: "id", Value: "conv-1"}}
	c.Request.Header.Set("Content-Type", "application/json")

	h := NewQASSEHandler(svc)
	h.Ask(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
}
