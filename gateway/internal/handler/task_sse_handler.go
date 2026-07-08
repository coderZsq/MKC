package handler

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/service"
	"github.com/zhushuangquan/mkc/gateway/pkg/response"
	"github.com/zhushuangquan/mkc/gateway/pkg/sse"
)

const heartbeatInterval = 30 * time.Second

// TaskSSEHandler exposes the Server-Sent Events endpoint for task progress.
type TaskSSEHandler struct {
	taskSvc     service.TaskService
	broadcaster service.TaskBroadcaster
}

// NewTaskSSEHandler creates a TaskSSEHandler.
func NewTaskSSEHandler(taskSvc service.TaskService, broadcaster service.TaskBroadcaster) *TaskSSEHandler {
	return &TaskSSEHandler{
		taskSvc:     taskSvc,
		broadcaster: broadcaster,
	}
}

// Stream establishes an SSE connection for a single task.
func (h *TaskSSEHandler) Stream(c *gin.Context) {
	userID := c.GetUint64("user_id")
	taskUUID := c.Param("task_id")

	task, err := h.taskSvc.Get(c.Request.Context(), userID, taskUUID)
	if err != nil {
		mapTaskError(c, err)
		return
	}

	flusher, ok := c.Writer.(http.Flusher)
	if !ok {
		response.InternalError(c)
		return
	}

	c.Header("Content-Type", "text/event-stream; charset=utf-8")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")
	c.Status(http.StatusOK)
	flusher.Flush()

	ctx, cancel := context.WithCancel(c.Request.Context())
	defer cancel()

	ch, err := h.broadcaster.Subscribe(ctx, taskUUID)
	if err != nil {
		response.Error(c, http.StatusServiceUnavailable, "TOO_MANY_SUBSCRIBERS", err.Error())
		return
	}

	if err := writeEvent(c.Writer, flusher, service.TaskEvent{
		EventType: "status",
		TaskID:    taskUUID,
		Progress:  task.Progress,
		Status:    task.Status,
		Timestamp: time.Now().UTC(),
	}); err != nil {
		return
	}

	ticker := time.NewTicker(heartbeatInterval)
	defer ticker.Stop()

	for {
		select {
		case event, ok := <-ch:
			if !ok {
				return
			}
			if err := writeEvent(c.Writer, flusher, event); err != nil {
				return
			}
			if event.Status == model.TaskStatusCompleted || event.Status == model.TaskStatusFailed {
				return
			}
		case <-ticker.C:
			if _, err := fmt.Fprint(c.Writer, "event: heartbeat\ndata: {}\n\n"); err != nil {
				return
			}
			flusher.Flush()
		case <-ctx.Done():
			return
		}
	}
}

func writeEvent(w http.ResponseWriter, flusher http.Flusher, event service.TaskEvent) error {
	payload, err := event.Marshal()
	if err != nil {
		return err
	}
	sse.WriteEvent(w, event.EventType, payload)
	flusher.Flush()
	return nil
}
