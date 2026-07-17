package tracing

import (
	"context"
	"fmt"
	"strings"

	"github.com/zhushuangquan/mkc/gateway/internal/config"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.37.0"
	"go.opentelemetry.io/otel/trace"
	"go.uber.org/zap"
)

// InitTracer configures the global OpenTelemetry tracer provider.
func InitTracer(ctx context.Context, cfg config.TracingConfig, logger *zap.Logger) (func(context.Context) error, trace.Tracer) {
	if logger == nil {
		logger = zap.NewNop()
	}
	otel.SetTextMapPropagator(propagation.TraceContext{})
	if !cfg.Enabled {
		provider := trace.NewNoopTracerProvider()
		otel.SetTracerProvider(provider)
		return func(context.Context) error { return nil }, provider.Tracer(cfg.ServiceName)
	}

	exporter, err := buildExporter(ctx, cfg)
	if err != nil {
		logger.Warn("tracing exporter init failed; falling back to noop", zap.Error(err))
		provider := trace.NewNoopTracerProvider()
		otel.SetTracerProvider(provider)
		return func(context.Context) error { return nil }, provider.Tracer(cfg.ServiceName)
	}

	serviceName := cfg.ServiceName
	if serviceName == "" {
		serviceName = "mkc-gateway"
	}
	res, err := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(semconv.SchemaURL, semconv.ServiceName(serviceName)),
	)
	if err != nil {
		logger.Warn("tracing resource init failed; using default resource", zap.Error(err))
		res = resource.Default()
	}
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.TraceIDRatioBased(cfg.SampleRatio)),
	)
	otel.SetTracerProvider(provider)
	return provider.Shutdown, provider.Tracer(serviceName)
}

func buildExporter(ctx context.Context, cfg config.TracingConfig) (sdktrace.SpanExporter, error) {
	switch strings.ToLower(cfg.Exporter) {
	case "", "noop":
		return stdouttrace.New(stdouttrace.WithPrettyPrint())
	case "console", "stdout":
		return stdouttrace.New(stdouttrace.WithPrettyPrint())
	case "otlp", "otlp_http", "http":
		if cfg.Endpoint == "" {
			return nil, fmt.Errorf("otlp endpoint is required")
		}
		endpoint := strings.TrimPrefix(strings.TrimPrefix(cfg.Endpoint, "http://"), "https://")
		return otlptracehttp.New(ctx, otlptracehttp.WithEndpoint(endpoint), otlptracehttp.WithInsecure())
	default:
		return nil, fmt.Errorf("unsupported tracing exporter %q", cfg.Exporter)
	}
}
