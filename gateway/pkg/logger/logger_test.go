package logger

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNew_Console(t *testing.T) {
	log, err := New("info", "console")
	require.NoError(t, err)
	assert.NotNil(t, log)
}

func TestNew_JSON(t *testing.T) {
	log, err := New("debug", "json")
	require.NoError(t, err)
	assert.NotNil(t, log)
}

func TestNew_InvalidLevel(t *testing.T) {
	log, err := New("invalid", "json")
	require.Error(t, err)
	assert.Nil(t, log)
	assert.Contains(t, err.Error(), "invalid log level")
}
