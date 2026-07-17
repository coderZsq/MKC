package metrics

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var latencyBuckets = []float64{0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30}

// Metrics owns Gateway Prometheus collectors.
type Metrics struct {
	registry        *prometheus.Registry
	requestsTotal   *prometheus.CounterVec
	errorsTotal     *prometheus.CounterVec
	requestDuration *prometheus.HistogramVec
}

// New creates a metrics registry with Gateway collectors.
func New(namespace string) (*Metrics, error) {
	if namespace == "" {
		namespace = "mkc"
	}
	registry := prometheus.NewRegistry()
	m := &Metrics{
		registry: registry,
		requestsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Namespace: namespace,
				Subsystem: "gateway",
				Name:      "http_requests_total",
				Help:      "Gateway HTTP requests by method, path, and status.",
			},
			[]string{"method", "path", "status"},
		),
		errorsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Namespace: namespace,
				Subsystem: "gateway",
				Name:      "http_errors_total",
				Help:      "Gateway HTTP errors by method, path, and status.",
			},
			[]string{"method", "path", "status"},
		),
		requestDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Namespace: namespace,
				Subsystem: "gateway",
				Name:      "http_request_duration_seconds",
				Help:      "Gateway HTTP request latency in seconds.",
				Buckets:   latencyBuckets,
			},
			[]string{"method", "path"},
		),
	}
	if err := registry.Register(m.requestsTotal); err != nil {
		return nil, err
	}
	if err := registry.Register(m.errorsTotal); err != nil {
		return nil, err
	}
	if err := registry.Register(m.requestDuration); err != nil {
		return nil, err
	}
	return m, nil
}

func (m *Metrics) Handler() gin.HandlerFunc {
	handler := promhttp.HandlerFor(m.registry, promhttp.HandlerOpts{})
	return func(c *gin.Context) {
		handler.ServeHTTP(c.Writer, c.Request)
	}
}

func (m *Metrics) Middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		c.Next()
		path := c.FullPath()
		if path == "" {
			path = c.Request.URL.Path
		}
		status := strconv.Itoa(c.Writer.Status())
		m.requestsTotal.WithLabelValues(c.Request.Method, path, status).Inc()
		m.requestDuration.WithLabelValues(c.Request.Method, path).Observe(time.Since(start).Seconds())
		if c.Writer.Status() >= http.StatusInternalServerError {
			m.errorsTotal.WithLabelValues(c.Request.Method, path, status).Inc()
		}
	}
}

func (m *Metrics) Registry() *prometheus.Registry {
	return m.registry
}
