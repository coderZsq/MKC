package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/config"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

// ChatMessage is a single turn in a conversation history.
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// QARequest is the payload sent to the AI Service streaming Q&A endpoint.
type QARequest struct {
	Question         string        `json:"question"`
	ConversationID   string        `json:"conversation_id"`
	MessageID        string        `json:"message_id"`
	UserID           string        `json:"user_id"`
	ResourceIDs      []string      `json:"resource_ids,omitempty"`
	History          []ChatMessage `json:"history,omitempty"`
	TopK             *int          `json:"top_k,omitempty"`
	ScoreThreshold   *float64      `json:"score_threshold,omitempty"`
	MaxContextTokens *int          `json:"max_context_tokens,omitempty"`
	Temperature      *float64      `json:"temperature,omitempty"`
	MaxTokens        *int          `json:"max_tokens,omitempty"`
}

// SSEEvent represents a single Server-Sent Event received from the AI Service.
type SSEEvent struct {
	Event string
	Data  []byte
	Raw   string
}

// AIClient streams Q&A events from the AI Service.
type AIClient interface {
	StreamQA(ctx context.Context, req QARequest) (<-chan SSEEvent, error)
}

// HTTPAIClient is an AIClient that calls the AI Service over HTTP.
type HTTPAIClient struct {
	client      *http.Client
	baseURL     string
	internalKey string
	timeout     time.Duration
}

// NewAIClient creates an AIClient from the application configuration.
func NewAIClient(cfg *config.Config) AIClient {
	timeout := cfg.QA.Timeout
	if timeout <= 0 {
		timeout = cfg.AIService.Timeout
	}
	if timeout <= 0 {
		timeout = 120 * time.Second
	}
	return &HTTPAIClient{
		client:      &http.Client{},
		baseURL:     strings.TrimRight(cfg.AIService.BaseURL, "/"),
		internalKey: cfg.AIService.InternalKey,
		timeout:     timeout,
	}
}

// StreamQA calls the AI Service Agent stream endpoint and returns a channel of SSE events.
func (c *HTTPAIClient) StreamQA(ctx context.Context, req QARequest) (<-chan SSEEvent, error) {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)

	body, err := json.Marshal(req)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to marshal QA request: %w", err)
	}

	endpoint := fmt.Sprintf("%s/ai/v1/agent/run", c.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to create QA request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("X-Internal-Key", c.internalKey)

	resp, err := c.client.Do(httpReq)
	if err != nil {
		cancel()
		return nil, apperrors.New(http.StatusServiceUnavailable, apperrors.CodeAIServiceUnavailable, "AI service is unavailable")
	}

	if resp.StatusCode != http.StatusOK {
		defer func() { _ = resp.Body.Close() }()
		cancel()
		respBody, _ := io.ReadAll(resp.Body)
		code := apperrors.CodeAIServiceUnavailable
		message := "AI service is unavailable"
		if resp.StatusCode >= 400 && resp.StatusCode < 500 {
			code = apperrors.CodeBadRequest
			message = "AI service rejected the request"
		}
		if len(respBody) > 0 {
			message = string(respBody)
		}
		return nil, apperrors.New(resp.StatusCode, code, message)
	}

	events := make(chan SSEEvent, 64)
	go c.readStream(ctx, cancel, resp.Body, events)
	return events, nil
}

func (c *HTTPAIClient) readStream(ctx context.Context, cancel context.CancelFunc, body io.ReadCloser, events chan<- SSEEvent) {
	defer close(events)
	defer func() { _ = body.Close() }()
	defer cancel()

	reader := bufio.NewReader(body)
	var eventType string
	var dataLines []string

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		line, err := reader.ReadString('\n')
		if line != "" {
			line = strings.TrimRight(line, "\r\n")
			if line == "" {
				c.flushEvent(eventType, dataLines, events)
				eventType = ""
				dataLines = nil
			} else if strings.HasPrefix(line, "event:") {
				eventType = strings.TrimSpace(strings.TrimPrefix(line, "event:"))
			} else if strings.HasPrefix(line, "data:") {
				dataLines = append(dataLines, strings.TrimSpace(strings.TrimPrefix(line, "data:")))
			}
		}

		if err != nil {
			if eventType != "" || len(dataLines) > 0 {
				c.flushEvent(eventType, dataLines, events)
			}
			return
		}
	}
}

func (c *HTTPAIClient) flushEvent(eventType string, dataLines []string, events chan<- SSEEvent) {
	if eventType == "" && len(dataLines) == 0 {
		return
	}
	if eventType == "" {
		eventType = "message"
	}
	data := []byte(strings.Join(dataLines, "\n"))
	raw := fmt.Sprintf("event: %s\ndata: %s\n\n", eventType, string(data))
	select {
	case events <- SSEEvent{Event: eventType, Data: data, Raw: raw}:
	default:
	}
}
