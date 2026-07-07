package password

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHashAndCheck(t *testing.T) {
	hash, err := Hash("secret-password")
	require.NoError(t, err)
	assert.NotEmpty(t, hash)

	assert.True(t, Check("secret-password", hash))
	assert.False(t, Check("wrong-password", hash))
}
