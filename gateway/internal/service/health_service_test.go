package service

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
)

type stubDependency struct {
	name string
	ok   bool
}

func (s *stubDependency) Name() string { return s.name }
func (s *stubDependency) Ping(context.Context) error {
	if !s.ok {
		return errors.New("down")
	}
	return nil
}

func TestHealthService_AllHealthy(t *testing.T) {
	svc := NewHealthService("0.1.0",
		&stubDependency{name: "mysql", ok: true},
		&stubDependency{name: "redis", ok: true},
	)

	status, code := svc.Check(context.Background())
	assert.Equal(t, 200, code)
	assert.Equal(t, "ok", status.Status)
	assert.Equal(t, "0.1.0", status.Version)
	assert.Equal(t, "ok", status.Checks["mysql"])
	assert.Equal(t, "ok", status.Checks["redis"])
}

func TestHealthService_Degraded(t *testing.T) {
	svc := NewHealthService("0.1.0",
		&stubDependency{name: "mysql", ok: true},
		&stubDependency{name: "redis", ok: false},
	)

	status, code := svc.Check(context.Background())
	assert.Equal(t, 503, code)
	assert.Equal(t, "degraded", status.Status)
	assert.Equal(t, "ok", status.Checks["mysql"])
	assert.Equal(t, "down", status.Checks["redis"])
}

func TestNoopDependency(t *testing.T) {
	dep := &NoopDependency{NameVal: "mysql"}
	assert.Equal(t, "mysql", dep.Name())
	assert.ErrorContains(t, dep.Ping(context.Background()), "mysql is not configured")
}
