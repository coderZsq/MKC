package sse

import (
	"fmt"
	"io"
)

// WriteEvent writes a single Server-Sent Event to w.
// event is the event type (e.g. "progress"). data is the JSON payload.
// It does not flush; callers should flush after writing if streaming.
func WriteEvent(w io.Writer, event string, data []byte) {
	_, _ = fmt.Fprintf(w, "event: %s\ndata: %s\n\n", event, data)
}
