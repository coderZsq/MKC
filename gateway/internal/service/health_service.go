package service

import (
	"context"
	"fmt"
)

// Dependency represents a service dependency that can be health-checked.
type Dependency interface {
	Name() string
	Ping(ctx context.Context) error
}

// HealthStatus is the payload returned by the health endpoint.
type HealthStatus struct {
	Status  string            `json:"status"`
	Version string            `json:"version"`
	Checks  map[string]string `json:"checks"`
}

// HealthService checks application dependencies.
type HealthService struct {
	version string
	deps    []Dependency
}

// NewHealthService creates a health service for the supplied dependencies.
func NewHealthService(version string, deps ...Dependency) *HealthService {
	return &HealthService{version: version, deps: deps}
}

// Check evaluates all dependencies and returns a health status plus HTTP code.
func (s *HealthService) Check(ctx context.Context) (*HealthStatus, int) {
	checks := make(map[string]string, len(s.deps))
	status := "ok"
	code := 200

	for _, dep := range s.deps {
		if err := dep.Ping(ctx); err != nil {
			checks[dep.Name()] = "down"
			status = "degraded"
			code = 503
		} else {
			checks[dep.Name()] = "ok"
		}
	}

	return &HealthStatus{
		Status:  status,
		Version: s.version,
		Checks:  checks,
	}, code
}

// NoopDependency is used when a dependency is unavailable.
type NoopDependency struct{ NameVal string }

func (n *NoopDependency) Name() string { return n.NameVal }
func (n *NoopDependency) Ping(context.Context) error {
	return fmt.Errorf("%s is not configured", n.NameVal)
}
