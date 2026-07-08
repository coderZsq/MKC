package storage

import (
	"net"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
)

func TestNewMinIOClient_InvalidEndpoint(t *testing.T) {
	cfg := config.MinIOConfig{
		Endpoint: "",
		Bucket:   "test-bucket",
	}

	client, err := NewMinIOClient(cfg)
	require.Error(t, err)
	assert.Nil(t, client)
	assert.Contains(t, err.Error(), "failed to create minio client")
}

func TestNewMinIOClient_BucketExistsError(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	addr := ln.Addr().String()
	require.NoError(t, ln.Close())

	cfg := config.MinIOConfig{
		Endpoint: addr,
		Bucket:   "test-bucket",
	}

	client, err := NewMinIOClient(cfg)
	require.Error(t, err)
	assert.Nil(t, client)
	assert.Contains(t, err.Error(), "failed to check bucket existence")
}
