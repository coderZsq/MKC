package repository

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/config"
)

func TestNewMySQL_ConnectionRefused(t *testing.T) {
	cfg := config.MySQLConfig{
		Host:            "127.0.0.1",
		Port:            1,
		User:            "mkc",
		Password:        "mkc",
		DBName:          "mkc",
		MaxOpenConns:    10,
		MaxIdleConns:    5,
		ConnMaxLifetime: time.Hour,
	}

	db, err := NewMySQL(cfg)
	require.Error(t, err)
	assert.Nil(t, db)
	assert.Contains(t, err.Error(), "failed to open mysql connection")
}
