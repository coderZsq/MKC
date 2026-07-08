package repository

import (
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func setupMigrateTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	db, err := gorm.Open(sqlite.Open(dbPath+"?_fk=1"), &gorm.Config{})
	require.NoError(t, err)
	return db
}

func countTables(t *testing.T, db *gorm.DB) int {
	t.Helper()
	var count int64
	err := db.Raw("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").Scan(&count).Error
	require.NoError(t, err)
	return int(count)
}

func TestAutoMigrate_CreatesTables(t *testing.T) {
	db := setupMigrateTestDB(t)

	require.NoError(t, AutoMigrate(db))

	assert.GreaterOrEqual(t, countTables(t, db), 5)

	for _, m := range []any{model.User{}, model.Resource{}, model.Task{}, model.Conversation{}, model.Message{}} {
		assert.True(t, db.Migrator().HasTable(m), "missing table for %T", m)
	}
}

func TestDropAll_RemovesTables(t *testing.T) {
	db := setupMigrateTestDB(t)

	require.NoError(t, AutoMigrate(db))
	require.GreaterOrEqual(t, countTables(t, db), 5)

	require.NoError(t, DropAll(db))

	assert.Equal(t, 0, countTables(t, db))
}

func TestDropAll_Error(t *testing.T) {
	db := setupMigrateTestDB(t)

	sqlDB, err := db.DB()
	require.NoError(t, err)
	require.NoError(t, sqlDB.Close())

	assert.Error(t, DropAll(db))
}
