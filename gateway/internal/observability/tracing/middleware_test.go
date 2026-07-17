package tracing

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"go.uber.org/zap"
)

func TestTracingMiddlewareCreatesRootSpan(t *testing.T) {
	// MKC-TC-S5-3-001: Gateway request creates a root span with method/path/status.
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(sdktrace.WithSyncer(exporter), sdktrace.WithSampler(sdktrace.AlwaysSample()))
	defer func() { _ = provider.Shutdown(context.Background()) }()
	otel.SetTracerProvider(provider)

	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(Middleware(provider.Tracer("test-gateway"), zap.NewNop()))
	r.GET("/test", func(c *gin.Context) { c.Status(http.StatusAccepted) })

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	r.ServeHTTP(w, req)

	spans := exporter.GetSpans()
	require.Len(t, spans, 1)
	assert.Equal(t, "GET /test", spans[0].Name)
	assert.Equal(t, http.StatusAccepted, w.Code)
	assert.NotEmpty(t, w.Header().Get("X-Trace-Id"))
}

func TestTracingMiddlewareMarksErrorSpan(t *testing.T) {
	// MKC-TC-S5-3-007: handler errors/status >=500 mark span as ERROR.
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(sdktrace.WithSyncer(exporter), sdktrace.WithSampler(sdktrace.AlwaysSample()))
	defer func() { _ = provider.Shutdown(context.Background()) }()

	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(Middleware(provider.Tracer("test-gateway"), zap.NewNop()))
	r.GET("/boom", func(c *gin.Context) { c.Status(http.StatusInternalServerError) })

	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/boom", nil)
	r.ServeHTTP(w, req)

	spans := exporter.GetSpans()
	require.Len(t, spans, 1)
	assert.Equal(t, "Error", spans[0].Status.Code.String())
}

func TestInjectTraceContextAddsTraceparent(t *testing.T) {
	// MKC-TC-S5-3-002: Gateway outbound request propagates traceparent.
	provider := sdktrace.NewTracerProvider(sdktrace.WithSampler(sdktrace.AlwaysSample()))
	defer func() { _ = provider.Shutdown(context.Background()) }()
	otel.SetTextMapPropagator(propagation.TraceContext{})
	ctx, span := provider.Tracer("test").Start(context.Background(), "parent")
	defer span.End()

	req := httptest.NewRequest(http.MethodPost, "http://ai.local/ai/v1/agent/run", nil)
	InjectTraceContext(ctx, req)

	assert.NotEmpty(t, req.Header.Get("traceparent"))
	assert.Contains(t, req.Header.Get("traceparent"), span.SpanContext().TraceID().String())
}
