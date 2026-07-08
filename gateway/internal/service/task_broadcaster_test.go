package service

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestTaskBroadcaster_SubscribeAndPublish(t *testing.T) {
	b := NewTaskBroadcaster()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	ch, err := b.Subscribe(ctx, "task-1")
	require.NoError(t, err)

	b.Publish(ctx, "task-1", TaskEvent{EventType: "progress", TaskID: "task-1", Progress: 25, Status: "running"})

	select {
	case evt := <-ch:
		assert.Equal(t, "progress", evt.EventType)
		assert.Equal(t, uint8(25), evt.Progress)
		assert.Equal(t, "running", evt.Status)
	case <-time.After(time.Second):
		t.Fatal("expected event")
	}
}

func TestTaskBroadcaster_SubscribeIsolatedByTask(t *testing.T) {
	b := NewTaskBroadcaster()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	ch1, err := b.Subscribe(ctx, "task-1")
	require.NoError(t, err)
	ch2, err := b.Subscribe(ctx, "task-2")
	require.NoError(t, err)

	b.Publish(ctx, "task-1", TaskEvent{EventType: "progress", TaskID: "task-1"})

	select {
	case <-ch1:
	case <-time.After(time.Second):
		t.Fatal("expected event on task-1")
	}

	select {
	case <-ch2:
		t.Fatal("unexpected event on task-2")
	case <-time.After(100 * time.Millisecond):
	}
}

func TestTaskBroadcaster_SubscriberLimit(t *testing.T) {
	b := NewTaskBroadcaster()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	for i := 0; i < defaultMaxSubscribersPerTask; i++ {
		_, err := b.Subscribe(ctx, "task-1")
		require.NoError(t, err)
	}

	_, err := b.Subscribe(ctx, "task-1")
	assert.ErrorIs(t, err, ErrTooManySubscribers)
}

func TestTaskBroadcaster_ContextCancelClosesChannel(t *testing.T) {
	b := NewTaskBroadcaster()
	ctx, cancel := context.WithCancel(context.Background())

	ch, err := b.Subscribe(ctx, "task-1")
	require.NoError(t, err)

	cancel()

	select {
	case <-ch:
	case <-time.After(time.Second):
		t.Fatal("expected channel to close")
	}
}

func TestTaskBroadcaster_CloseClosesChannels(t *testing.T) {
	b := NewTaskBroadcaster()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	ch, err := b.Subscribe(ctx, "task-1")
	require.NoError(t, err)

	b.Close("task-1")

	select {
	case <-ch:
	case <-time.After(time.Second):
		t.Fatal("expected channel to close")
	}
}

func TestTaskBroadcaster_NonBlockingPublishDropsForSlowConsumer(t *testing.T) {
	b := NewTaskBroadcaster()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	ch, err := b.Subscribe(ctx, "task-1")
	require.NoError(t, err)

	// Fill the subscriber buffer without reading.
	for i := 0; i < subscriberBufferSize+2; i++ {
		b.Publish(ctx, "task-1", TaskEvent{EventType: "progress", TaskID: "task-1", Progress: uint8(i)})
	}

	readCount := 0
	drain:
	for {
		select {
		case <-ch:
			readCount++
		case <-time.After(100 * time.Millisecond):
			break drain
		}
	}

	assert.LessOrEqual(t, readCount, subscriberBufferSize)
}

func TestTaskEvent_ToSSE(t *testing.T) {
	evt := TaskEvent{
		EventType: "done",
		TaskID:    "task-1",
		Progress:  100,
		Status:    "completed",
		Timestamp: time.Unix(0, 0).UTC(),
	}

	sse := evt.ToSSE()
	assert.Contains(t, sse, "event: done")
	assert.Contains(t, sse, `"task_id":"task-1"`)
	assert.Contains(t, sse, `"status":"completed"`)
	assert.Contains(t, sse, `"progress":100`)
}
