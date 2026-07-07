package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoad_Defaults(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	content := `
app:
  name: test-gateway
  version: 0.0.1
  env: dev

server:
  port: 8080
  mode: debug

log:
  level: debug
  format: console

mysql:
  host: localhost
  port: 3306
  user: mkc
  password: ""
  dbname: mkc

redis:
  addr: localhost:6379
  password: ""
  db: 0

jwt:
  secret: test-secret
  access_ttl: 15m
  refresh_ttl: 168h

ai_service:
  base_url: http://localhost:5000
  timeout: 60s
`
	require.NoError(t, os.WriteFile(path, []byte(content), 0644))

	cfg, err := Load(path)
	require.NoError(t, err)
	assert.Equal(t, "test-gateway", cfg.App.Name)
	assert.Equal(t, 8080, cfg.Server.Port)
	assert.Equal(t, "debug", cfg.Log.Level)
	assert.Equal(t, "console", cfg.Log.Format)
	assert.Equal(t, "localhost:6379", cfg.Redis.Addr)
}

func TestLoad_EnvOverride(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	content := `
app:
  name: test-gateway
  version: 0.0.1
  env: dev

server:
  port: 8080
  mode: debug

log:
  level: info
  format: json

mysql:
  host: localhost
  port: 3306
  user: mkc
  password: ""
  dbname: mkc

redis:
  addr: localhost:6379
  password: ""
  db: 0

jwt:
  secret: test-secret
  access_ttl: 15m
  refresh_ttl: 168h

ai_service:
  base_url: http://localhost:5000
  timeout: 60s
`
	require.NoError(t, os.WriteFile(path, []byte(content), 0644))
	t.Setenv("APP_SERVER_PORT", "9090")

	cfg, err := Load(path)
	require.NoError(t, err)
	assert.Equal(t, 9090, cfg.Server.Port)
}

func TestLoad_InvalidPort(t *testing.T) {
	cfg := &Config{Server: ServerConfig{Port: 0}}
	assert.Error(t, cfg.validate())
}
