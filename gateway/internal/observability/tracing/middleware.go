package tracing

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
	"go.opentelemetry.io/otel/trace/noop"
)

const TraceIDKey = "trace_id"

// Middleware creates a server span for each HTTP request.
func Middleware(tracer trace.Tracer) gin.HandlerFunc {
	if tracer == nil {
		tracer = noop.NewTracerProvider().Tracer("noop")
	}
	return func(c *gin.Context) {
		start := time.Now()
		spanName := c.FullPath()
		if spanName == "" {
			spanName = c.Request.URL.Path
		}
		spanName = c.Request.Method + " " + spanName
		ctx, span := tracer.Start(c.Request.Context(), spanName, trace.WithSpanKind(trace.SpanKindServer))
		defer span.End()
		c.Request = c.Request.WithContext(ctx)

		traceID := span.SpanContext().TraceID().String()
		if span.SpanContext().IsValid() {
			c.Set(TraceIDKey, traceID)
			c.Header("X-Trace-Id", traceID)
		}

		c.Next()

		status := c.Writer.Status()
		span.SetAttributes(
			attribute.String("http.request.method", c.Request.Method),
			attribute.String("url.path", c.Request.URL.Path),
			attribute.Int("http.response.status_code", status),
			attribute.Int64("http.server.duration_ms", time.Since(start).Milliseconds()),
		)
		if len(c.Errors) > 0 || status >= http.StatusInternalServerError {
			span.SetStatus(codes.Error, sanitizedErrorCode(c))
			span.SetAttributes(attribute.String("error.code", sanitizedErrorCode(c)))
		}
	}
}

func sanitizedErrorCode(c *gin.Context) string {
	if len(c.Errors) == 0 {
		return "HTTP_ERROR"
	}
	return "HANDLER_ERROR"
}
