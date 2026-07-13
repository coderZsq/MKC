package service

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
)

func TestAIClient_StreamQA_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/ai/v1/agent/run", r.URL.Path)
		assert.Equal(t, "secret", r.Header.Get("X-Internal-Key"))
		assert.Equal(t, "application/json", r.Header.Get("Content-Type"))

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("event: chunk\ndata: {\"delta\": \"hello\"}\n\n"))
		_, _ = w.Write([]byte("event: done\ndata: {\"finish_reason\": \"stop\"}\n\n"))
		if f, ok := w.(http.Flusher); ok {
			f.Flush()
		}
	}))
	defer server.Close()

	client := NewAIClient(&config.Config{
		AIService: config.AIServiceConfig{BaseURL: server.URL, InternalKey: "secret", Timeout: 10 * time.Second},
		QA:        config.QAConfig{Timeout: 10 * time.Second},
	})

	events, err := client.StreamQA(context.Background(), QARequest{Question: "q"})
	require.NoError(t, err)

	var collected []SSEEvent
	for ev := range events {
		collected = append(collected, ev)
	}

	require.Len(t, collected, 2)
	assert.Equal(t, "chunk", collected[0].Event)
	assert.Equal(t, "done", collected[1].Event)
}

func TestAIClient_StreamQA_NonOKStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte(""))
	}))
	defer server.Close()

	client := NewAIClient(&config.Config{
		AIService: config.AIServiceConfig{BaseURL: server.URL, InternalKey: "secret"},
		QA:        config.QAConfig{Timeout: 10 * time.Second},
	})

	_, err := client.StreamQA(context.Background(), QARequest{Question: "q"})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "AI service")
}

func TestAIClient_StreamQA_ConnectionError(t *testing.T) {
	client := NewAIClient(
		&config.Config{
			AIService: config.AIServiceConfig{BaseURL: "http://localhost:1", InternalKey: "secret"},
			QA:        config.QAConfig{Timeout: 1 * time.Second},
		},
	)

	_, err := client.StreamQA(context.Background(), QARequest{Question: "q"})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "AI service is unavailable")
}
