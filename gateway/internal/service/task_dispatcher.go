package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"go.uber.org/zap"
)

// TaskDispatcher dispatches pending tasks to the AI Service for execution.
type TaskDispatcher interface {
	Dispatch(ctx context.Context, task *model.Task, resource *model.Resource) error
	DispatchSummary(ctx context.Context, resource *model.Resource, payload SummaryDispatchPayload) error
}

// HTTPTaskDispatcher dispatches tasks by calling the AI Service HTTP endpoints.
type HTTPTaskDispatcher struct {
	client          *http.Client
	baseURL         string
	internalKey     string
	bucket          string
	dispatchTimeout time.Duration
	logger          *zap.Logger
}

// NewTaskDispatcher creates a TaskDispatcher that posts to the AI Service.
func NewTaskDispatcher(cfg *config.Config, logger *zap.Logger) TaskDispatcher {
	if logger == nil {
		logger = zap.NewNop()
	}
	timeout := cfg.Task.DispatchTimeout
	if timeout <= 0 {
		timeout = 10 * time.Second
	}
	return &HTTPTaskDispatcher{
		client: &http.Client{
			Timeout: timeout,
		},
		baseURL:         strings.TrimRight(cfg.AIService.BaseURL, "/"),
		internalKey:     cfg.AIService.InternalKey,
		bucket:          cfg.MinIO.Bucket,
		dispatchTimeout: timeout,
		logger:          logger,
	}
}

// Dispatch sends the task to the appropriate AI Service endpoint.
func (d *HTTPTaskDispatcher) Dispatch(ctx context.Context, task *model.Task, resource *model.Resource) error {
	if task == nil {
		return fmt.Errorf("task is nil")
	}
	if resource == nil || resource.UUID == "" {
		return fmt.Errorf("task resource is missing")
	}

	endpoint, payload, err := d.buildDispatchRequest(task, resource)
	if err != nil {
		return err
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal dispatch payload: %w", err)
	}

	ctx, cancel := context.WithTimeout(ctx, d.dispatchTimeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("failed to create dispatch request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", d.internalKey)

	resp, err := d.client.Do(req)
	if err != nil {
		d.logger.Warn("task dispatch request failed", zap.String("task_id", task.UUID), zap.Error(err))
		return apperrors.WorkerUnavailable("AI service is unavailable")
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode == http.StatusAccepted {
		return nil
	}

	respBody, _ := io.ReadAll(resp.Body)
	d.logger.Warn("task dispatch returned non-accepted status",
		zap.String("task_id", task.UUID),
		zap.Int("status", resp.StatusCode),
		zap.ByteString("response", respBody),
	)

	if resp.StatusCode >= 500 {
		return apperrors.WorkerUnavailable("AI service is unavailable")
	}
	return apperrors.DispatchFailed("AI service rejected the task")
}

// DispatchSummary sends a summary generation request to the AI Service.
func (d *HTTPTaskDispatcher) DispatchSummary(ctx context.Context, resource *model.Resource, payload SummaryDispatchPayload) error {
	if resource == nil || resource.UUID == "" {
		return fmt.Errorf("summary resource is missing")
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal summary payload: %w", err)
	}

	ctx, cancel := context.WithTimeout(ctx, d.dispatchTimeout)
	defer cancel()

	endpoint := fmt.Sprintf("%s/ai/v1/resources/%s/summarize", d.baseURL, resource.UUID)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("failed to create summary dispatch request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", d.internalKey)

	resp, err := d.client.Do(req)
	if err != nil {
		d.logger.Warn("summary dispatch request failed", zap.String("resource_id", resource.UUID), zap.Error(err))
		return apperrors.WorkerUnavailable("AI service is unavailable")
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode == http.StatusAccepted {
		return nil
	}

	respBody, _ := io.ReadAll(resp.Body)
	d.logger.Warn("summary dispatch returned non-accepted status",
		zap.String("resource_id", resource.UUID),
		zap.Int("status", resp.StatusCode),
		zap.ByteString("response", respBody),
	)

	if resp.StatusCode >= 500 {
		return apperrors.WorkerUnavailable("AI service is unavailable")
	}
	return apperrors.DispatchFailed("AI service rejected the summary task")
}

func (d *HTTPTaskDispatcher) buildDispatchRequest(task *model.Task, resource *model.Resource) (string, any, error) {
	storageURL := fmt.Sprintf("minio://%s/%s", d.bucket, resource.StorageKey)

	switch task.Type {
	case model.TaskTypeMediaParse:
		endpoint := fmt.Sprintf("%s/ai/v1/asr", d.baseURL)
		payload := asrDispatchRequest{
			TaskID:     task.UUID,
			ResourceID: resource.UUID,
			AudioURL:   storageURL,
			Language:   "zh",
			Model:      "small",
		}
		return endpoint, payload, nil
	case model.TaskTypePdfParse:
		endpoint := fmt.Sprintf("%s/ai/v1/pdf/parse", d.baseURL)
		payload := pdfDispatchRequest{
			TaskID:     task.UUID,
			ResourceID: resource.UUID,
			PDFURL:     storageURL,
		}
		return endpoint, payload, nil
	default:
		return "", nil, fmt.Errorf("unsupported task type for dispatch: %s", task.Type)
	}
}

type asrDispatchRequest struct {
	TaskID     string `json:"task_id"`
	ResourceID string `json:"resource_id"`
	AudioURL   string `json:"audio_url"`
	Language   string `json:"language,omitempty"`
	Model      string `json:"model,omitempty"`
}

type pdfDispatchRequest struct {
	TaskID     string `json:"task_id"`
	ResourceID string `json:"resource_id"`
	PDFURL     string `json:"pdf_url"`
}

// SummaryDispatchPayload is sent to AI Service for summary generation.
type SummaryDispatchPayload struct {
	Types       []string         `json:"types"`
	SourceType  string           `json:"source_type"`
	Content     string           `json:"content,omitempty"`
	Parsed      map[string]any   `json:"parsed,omitempty"`
	SRTSegments []map[string]any `json:"srt_segments,omitempty"`
	TaskID      string           `json:"task_id,omitempty"`
}
