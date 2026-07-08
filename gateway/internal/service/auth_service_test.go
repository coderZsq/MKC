package service

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
)

type stubUserRepository struct {
	createFunc     func(ctx context.Context, user *model.User) error
	getByEmailFunc func(ctx context.Context, email string) (*model.User, error)
	getByUUIDFunc  func(ctx context.Context, uuid string) (*model.User, error)
}

func (s *stubUserRepository) Create(ctx context.Context, user *model.User) error {
	if s.createFunc != nil {
		return s.createFunc(ctx, user)
	}
	return nil
}

func (s *stubUserRepository) GetByEmail(ctx context.Context, email string) (*model.User, error) {
	if s.getByEmailFunc != nil {
		return s.getByEmailFunc(ctx, email)
	}
	return nil, nil
}

func (s *stubUserRepository) GetByUUID(ctx context.Context, uuid string) (*model.User, error) {
	if s.getByUUIDFunc != nil {
		return s.getByUUIDFunc(ctx, uuid)
	}
	return nil, nil
}

type stubTokenStore struct {
	saveFunc           func(ctx context.Context, userUUID, tokenUUID string, session []byte, ttl time.Duration) error
	getFunc            func(ctx context.Context, userUUID, tokenUUID string) ([]byte, error)
	deleteFunc         func(ctx context.Context, userUUID, tokenUUID string) error
	findByTokenUUIDFunc func(ctx context.Context, tokenUUID string) (string, []byte, error)
}

func (s *stubTokenStore) Save(ctx context.Context, userUUID, tokenUUID string, session []byte, ttl time.Duration) error {
	if s.saveFunc != nil {
		return s.saveFunc(ctx, userUUID, tokenUUID, session, ttl)
	}
	return nil
}

func (s *stubTokenStore) Get(ctx context.Context, userUUID, tokenUUID string) ([]byte, error) {
	if s.getFunc != nil {
		return s.getFunc(ctx, userUUID, tokenUUID)
	}
	return nil, nil
}

func (s *stubTokenStore) Delete(ctx context.Context, userUUID, tokenUUID string) error {
	if s.deleteFunc != nil {
		return s.deleteFunc(ctx, userUUID, tokenUUID)
	}
	return nil
}

func (s *stubTokenStore) FindByTokenUUID(ctx context.Context, tokenUUID string) (string, []byte, error) {
	if s.findByTokenUUIDFunc != nil {
		return s.findByTokenUUIDFunc(ctx, tokenUUID)
	}
	return "", nil, nil
}

type stubPasswordHasher struct {
	hashFunc  func(password string) (string, error)
	checkFunc func(password, hash string) bool
}

func (s *stubPasswordHasher) Hash(password string) (string, error) {
	if s.hashFunc != nil {
		return s.hashFunc(password)
	}
	return password, nil
}

func (s *stubPasswordHasher) Check(password, hash string) bool {
	if s.checkFunc != nil {
		return s.checkFunc(password, hash)
	}
	return password == hash
}

func newTestAuthService(t *testing.T) (*authService, *stubUserRepository, *stubTokenStore, *stubPasswordHasher) {
	jwtMgr := jwt.NewManager("test-secret", time.Hour, 24*time.Hour)
	userRepo := &stubUserRepository{}
	tokenStore := &stubTokenStore{}
	hasher := &stubPasswordHasher{}
	svc := NewAuthService(userRepo, tokenStore, jwtMgr, hasher).(*authService)
	return svc, userRepo, tokenStore, hasher
}

func TestAuthService_Register_Success(t *testing.T) {
	svc, _, tokenStore, hasher := newTestAuthService(t)
	hasher.hashFunc = func(password string) (string, error) {
		return "hashed-" + password, nil
	}
	tokenStore.saveFunc = func(ctx context.Context, userUUID, tokenUUID string, session []byte, ttl time.Duration) error {
		assert.NotEmpty(t, userUUID)
		assert.NotEmpty(t, tokenUUID)
		assert.Greater(t, ttl, time.Duration(0))
		return nil
	}

	resp, err := svc.Register(context.Background(), RegisterRequest{
		Email:    "alice@example.com",
		Password: "Password1",
		Nickname: "Alice",
	})
	require.NoError(t, err)
	assert.NotEmpty(t, resp.UserID)
	assert.Equal(t, "alice@example.com", resp.Email)
	assert.Equal(t, "Alice", resp.Nickname)
	assert.NotEmpty(t, resp.AccessToken)
	assert.NotEmpty(t, resp.RefreshToken)
	assert.Equal(t, "Bearer", resp.TokenType)
}

func TestAuthService_Register_Validation(t *testing.T) {
	svc, _, _, _ := newTestAuthService(t)

	_, err := svc.Register(context.Background(), RegisterRequest{
		Email:    "not-email",
		Password: "Password1",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "VALIDATION")

	_, err = svc.Register(context.Background(), RegisterRequest{
		Email:    "alice@example.com",
		Password: "short1",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "password")

	_, err = svc.Register(context.Background(), RegisterRequest{
		Email:    "alice@example.com",
		Password: "onlyletters",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "password")
}

func TestAuthService_Login_Success(t *testing.T) {
	svc, userRepo, _, hasher := newTestAuthService(t)
	userRepo.getByEmailFunc = func(ctx context.Context, email string) (*model.User, error) {
		return &model.User{UUID: uuid.NewString(), Email: email, PasswordHash: "hashed-pass", Nickname: "Alice"}, nil
	}
	hasher.checkFunc = func(password, hash string) bool {
		return password == "Password1" && hash == "hashed-pass"
	}

	resp, err := svc.Login(context.Background(), LoginRequest{
		Email:    "alice@example.com",
		Password: "Password1",
	})
	require.NoError(t, err)
	assert.NotEmpty(t, resp.AccessToken)
	assert.NotEmpty(t, resp.RefreshToken)
}

func TestAuthService_Login_InvalidCredentials(t *testing.T) {
	svc, userRepo, _, hasher := newTestAuthService(t)
	userRepo.getByEmailFunc = func(ctx context.Context, email string) (*model.User, error) {
		return &model.User{UUID: uuid.NewString(), Email: email, PasswordHash: "hashed-pass"}, nil
	}
	hasher.checkFunc = func(password, hash string) bool { return false }

	_, err := svc.Login(context.Background(), LoginRequest{
		Email:    "alice@example.com",
		Password: "wrong",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "AUTH_INVALID_CREDENTIALS")
}

func TestAuthService_Login_UserNotFound(t *testing.T) {
	svc, userRepo, _, _ := newTestAuthService(t)
	userRepo.getByEmailFunc = func(ctx context.Context, email string) (*model.User, error) {
		return nil, repository.ErrNotFound
	}

	_, err := svc.Login(context.Background(), LoginRequest{
		Email:    "missing@example.com",
		Password: "Password1",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "AUTH_INVALID_CREDENTIALS")
}

func TestAuthService_Refresh_Success(t *testing.T) {
	svc, userRepo, tokenStore, _ := newTestAuthService(t)
	userUUID := uuid.NewString()
	tokenUUID := uuid.NewString()
	userRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.User, error) {
		return &model.User{UUID: userUUID, Email: "alice@example.com"}, nil
	}
	tokenStore.findByTokenUUIDFunc = func(ctx context.Context, rt string) (string, []byte, error) {
		assert.Equal(t, tokenUUID, rt)
		return userUUID, []byte(`{}`), nil
	}
	tokenStore.deleteFunc = func(ctx context.Context, uu, rt string) error {
		assert.Equal(t, userUUID, uu)
		assert.Equal(t, tokenUUID, rt)
		return nil
	}

	resp, err := svc.Refresh(context.Background(), tokenUUID)
	require.NoError(t, err)
	assert.NotEmpty(t, resp.AccessToken)
	assert.Equal(t, "Bearer", resp.TokenType)
}

func TestAuthService_Refresh_InvalidToken(t *testing.T) {
	svc, _, tokenStore, _ := newTestAuthService(t)
	tokenStore.findByTokenUUIDFunc = func(ctx context.Context, rt string) (string, []byte, error) {
		return "", nil, errors.New("not found")
	}

	_, err := svc.Refresh(context.Background(), uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "AUTH_SESSION_EXPIRED")
}

func TestAuthService_Logout_Success(t *testing.T) {
	svc, _, tokenStore, _ := newTestAuthService(t)
	userUUID := uuid.NewString()
	tokenUUID := uuid.NewString()
	tokenStore.deleteFunc = func(ctx context.Context, uu, rt string) error {
		assert.Equal(t, userUUID, uu)
		assert.Equal(t, tokenUUID, rt)
		return nil
	}

	require.NoError(t, svc.Logout(context.Background(), userUUID, tokenUUID))
}

func TestAuthService_Register_UserRepoError(t *testing.T) {
	svc, userRepo, _, _ := newTestAuthService(t)
	userRepo.createFunc = func(ctx context.Context, user *model.User) error {
		return apperrors.Conflict("email already exists")
	}

	_, err := svc.Register(context.Background(), RegisterRequest{
		Email:    "dupe@example.com",
		Password: "Password1",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "CONFLICT")
}

func TestAuthService_Register_HashError(t *testing.T) {
	svc, _, _, hasher := newTestAuthService(t)
	hasher.hashFunc = func(password string) (string, error) {
		return "", errors.New("hash failed")
	}

	_, err := svc.Register(context.Background(), RegisterRequest{
		Email:    "alice@example.com",
		Password: "Password1",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "INTERNAL_ERROR")
}

func TestAuthService_Register_TokenStoreSaveError(t *testing.T) {
	svc, _, tokenStore, hasher := newTestAuthService(t)
	hasher.hashFunc = func(password string) (string, error) {
		return "hashed", nil
	}
	tokenStore.saveFunc = func(ctx context.Context, userUUID, tokenUUID string, session []byte, ttl time.Duration) error {
		return errors.New("save failed")
	}

	_, err := svc.Register(context.Background(), RegisterRequest{
		Email:    "alice@example.com",
		Password: "Password1",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "save refresh session")
}

func TestAuthService_Login_InternalError(t *testing.T) {
	svc, userRepo, _, _ := newTestAuthService(t)
	userRepo.getByEmailFunc = func(ctx context.Context, email string) (*model.User, error) {
		return nil, errors.New("db down")
	}

	_, err := svc.Login(context.Background(), LoginRequest{
		Email:    "alice@example.com",
		Password: "Password1",
	})
	require.Error(t, err)
	assert.Contains(t, err.Error(), "INTERNAL_ERROR")
}

func TestAuthService_Refresh_InvalidSessionJSON(t *testing.T) {
	svc, _, tokenStore, _ := newTestAuthService(t)
	tokenStore.findByTokenUUIDFunc = func(ctx context.Context, rt string) (string, []byte, error) {
		return "user-uuid", []byte(`not-json`), nil
	}

	_, err := svc.Refresh(context.Background(), uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "AUTH_SESSION_EXPIRED")
}

func TestAuthService_Refresh_UserNotFound(t *testing.T) {
	svc, userRepo, tokenStore, _ := newTestAuthService(t)
	tokenStore.findByTokenUUIDFunc = func(ctx context.Context, rt string) (string, []byte, error) {
		return "user-uuid", []byte(`{}`), nil
	}
	userRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.User, error) {
		return nil, repository.ErrNotFound
	}

	_, err := svc.Refresh(context.Background(), uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "AUTH_SESSION_EXPIRED")
}

func TestAuthService_Refresh_DeleteError(t *testing.T) {
	svc, userRepo, tokenStore, _ := newTestAuthService(t)
	userRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.User, error) {
		return &model.User{UUID: uuid, Email: "alice@example.com"}, nil
	}
	tokenStore.findByTokenUUIDFunc = func(ctx context.Context, rt string) (string, []byte, error) {
		return "user-uuid", []byte(`{}`), nil
	}
	tokenStore.deleteFunc = func(ctx context.Context, uu, rt string) error {
		return errors.New("delete failed")
	}

	_, err := svc.Refresh(context.Background(), uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "delete refresh session")
}

func TestAuthService_Logout_DeleteError(t *testing.T) {
	svc, _, tokenStore, _ := newTestAuthService(t)
	tokenStore.deleteFunc = func(ctx context.Context, uu, rt string) error {
		return errors.New("delete failed")
	}

	err := svc.Logout(context.Background(), uuid.NewString(), uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "delete refresh session")
}

func TestAuthService_Me_NotFound(t *testing.T) {
	svc, userRepo, _, _ := newTestAuthService(t)
	userRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.User, error) {
		return nil, repository.ErrNotFound
	}

	_, err := svc.Me(context.Background(), uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "NOT_FOUND")
}

func TestAuthService_Me_InternalError(t *testing.T) {
	svc, userRepo, _, _ := newTestAuthService(t)
	userRepo.getByUUIDFunc = func(ctx context.Context, uuid string) (*model.User, error) {
		return nil, errors.New("db down")
	}

	_, err := svc.Me(context.Background(), uuid.NewString())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "INTERNAL_ERROR")
}

func TestBcryptHasher(t *testing.T) {
	h := BcryptHasher{}
	hash, err := h.Hash("Password1")
	require.NoError(t, err)
	assert.True(t, h.Check("Password1", hash))
	assert.False(t, h.Check("wrong", hash))
}
