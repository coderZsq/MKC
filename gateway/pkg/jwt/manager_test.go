package jwt

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestManager_TTLs(t *testing.T) {
	accessTTL := 15 * time.Minute
	refreshTTL := 7 * 24 * time.Hour
	m := NewManager("test-secret", accessTTL, refreshTTL)

	assert.Equal(t, accessTTL, m.AccessTTL())
	assert.Equal(t, refreshTTL, m.RefreshTTL())
}

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

func TestParseAccessToken_Expired(t *testing.T) {
	m := NewManager("test-secret", -time.Hour, 7*24*time.Hour)

	token, err := m.GenerateAccessToken("user-uuid", "user@example.com")
	require.NoError(t, err)

	_, err = m.ParseAccessToken(token)
	assert.Error(t, err)
}
