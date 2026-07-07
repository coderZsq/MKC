package jwt

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestGenerateAndParseAccessToken(t *testing.T) {
	m := NewManager("test-secret", 15*time.Minute, 7*24*time.Hour)

	token, err := m.GenerateAccessToken("user-uuid", "user@example.com")
	require.NoError(t, err)
	assert.NotEmpty(t, token)

	claims, err := m.ParseAccessToken(token)
	require.NoError(t, err)
	assert.Equal(t, "user-uuid", claims.Subject)
	assert.Equal(t, "user@example.com", claims.Email)
}

func TestParseAccessToken_Invalid(t *testing.T) {
	m := NewManager("test-secret", 15*time.Minute, 7*24*time.Hour)

	_, err := m.ParseAccessToken("not.a.token")
	assert.Error(t, err)
}
