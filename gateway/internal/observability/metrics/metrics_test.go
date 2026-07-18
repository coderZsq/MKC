package metrics

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestMetricsHandlerExposesPrometheusText(t *testing.T) {
	// MKC-TC-S5-4-001: Gateway /metrics returns Prometheus text.
	collector, err := New("mkc")
	require.NoError(t, err)

	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(collector.Middleware())
	r.GET("/metrics", collector.Handler())
	r.GET("/ping", func(c *gin.Context) { c.Status(http.StatusOK) })

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/ping", nil))
	require.Equal(t, http.StatusOK, w.Code)

	metrics := httptest.NewRecorder()
	r.ServeHTTP(metrics, httptest.NewRequest(http.MethodGet, "/metrics", nil))

	assert.Equal(t, http.StatusOK, metrics.Code)
	body := metrics.Body.String()
	assert.Contains(t, body, "mkc_gateway_http_requests_total")
	assert.Contains(t, body, "mkc_gateway_http_request_duration_seconds_bucket")
	assert.NotContains(t, strings.ToLower(body), "authorization")
	assert.NotContains(t, strings.ToLower(body), "jwt")
}

func TestDuplicateCollectorRegistrationReturnsError(t *testing.T) {
	// MKC-TC-S5-4-009: duplicate registration is detectable.
	collector, err := New("mkc")
	require.NoError(t, err)

	err = collector.Registry().Register(collector.requestsTotal)

	require.Error(t, err)
}

func TestMetricsDisabledRouteNotRegistered(t *testing.T) {
	// MKC-TC-S5-4-008: disabled metrics returns 404.
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/health", func(c *gin.Context) { c.Status(http.StatusOK) })

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/metrics", nil))

	assert.Equal(t, http.StatusNotFound, w.Code)
}
