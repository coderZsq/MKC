package service

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/zhushuangquan/mkc/gateway/pkg/sse"
)

// TaskEvent represents a single event broadcast to task subscribers.
type TaskEvent struct {
	EventID   string    `json:"-"`
	EventType string    `json:"-"`
	TaskID    string    `json:"task_id"`
	Progress  uint8     `json:"progress"`
	Status    string    `json:"status"`
	Message   *string   `json:"message"`
	Timestamp time.Time `json:"timestamp"`
}

// Marshal returns the JSON payload of the event.
func (e TaskEvent) Marshal() ([]byte, error) {
	return json.Marshal(e)
}

// ToSSE serializes the event to the SSE wire format.
func (e TaskEvent) ToSSE() string {
	data, err := e.Marshal()
	if err != nil {
		return ""
	}
	var buf bytes.Buffer
	sse.WriteEvent(&buf, e.EventType, data)
	return buf.String()
}

// TaskBroadcaster manages in-memory subscriptions for task events.
type TaskBroadcaster interface {
	Subscribe(ctx context.Context, taskID string) (<-chan TaskEvent, error)
	Publish(ctx context.Context, taskID string, event TaskEvent)
	Close(taskID string)
}

const defaultMaxSubscribersPerTask = 10
const subscriberBufferSize = 4

// NewTaskBroadcaster creates an in-memory TaskBroadcaster.
func NewTaskBroadcaster() TaskBroadcaster {
	return &inMemoryTaskBroadcaster{
		subs:              make(map[string][]chan TaskEvent),
		maxSubscribers:    defaultMaxSubscribersPerTask,
		subscriberBufSize: subscriberBufferSize,
	}
}

type inMemoryTaskBroadcaster struct {
	mu                sync.RWMutex
	subs              map[string][]chan TaskEvent
	maxSubscribers    int
	subscriberBufSize int
}

// ErrTooManySubscribers is returned when a task reaches its subscriber limit.
var ErrTooManySubscribers = errors.New("too many subscribers for this task")

func (b *inMemoryTaskBroadcaster) Subscribe(ctx context.Context, taskID string) (<-chan TaskEvent, error) {
	b.mu.Lock()
	if len(b.subs[taskID]) >= b.maxSubscribers {
		b.mu.Unlock()
		return nil, ErrTooManySubscribers
	}

	ch := make(chan TaskEvent, b.subscriberBufSize)
	b.subs[taskID] = append(b.subs[taskID], ch)
	b.mu.Unlock()

	go func() {
		<-ctx.Done()
		b.removeSubscriber(taskID, ch)
	}()

	return ch, nil
}

func (b *inMemoryTaskBroadcaster) Publish(ctx context.Context, taskID string, event TaskEvent) {
	b.mu.RLock()
	subs := make([]chan TaskEvent, len(b.subs[taskID]))
	copy(subs, b.subs[taskID])
	b.mu.RUnlock()

	for _, ch := range subs {
		select {
		case ch <- event:
		case <-ctx.Done():
			return
		default:
			// Drop event for slow consumers to avoid blocking publishers.
		}
	}
}

func (b *inMemoryTaskBroadcaster) Close(taskID string) {
	b.mu.Lock()
	subs := b.subs[taskID]
	delete(b.subs, taskID)
	b.mu.Unlock()

	for _, ch := range subs {
		close(ch)
	}
}

func (b *inMemoryTaskBroadcaster) removeSubscriber(taskID string, ch chan TaskEvent) {
	b.mu.Lock()
	defer b.mu.Unlock()

	subs := b.subs[taskID]
	for i, c := range subs {
		if c == ch {
			b.subs[taskID] = append(subs[:i], subs[i+1:]...)
			close(ch)
			break
		}
	}
	if len(b.subs[taskID]) == 0 {
		delete(b.subs, taskID)
	}
}

// String implements fmt.Stringer for debug logging.
func (e TaskEvent) String() string {
	return fmt.Sprintf("TaskEvent{type=%s task=%s status=%s progress=%d}", e.EventType, e.TaskID, e.Status, e.Progress)
}
