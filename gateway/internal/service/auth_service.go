package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"

	"github.com/google/uuid"
	"github.com/zhushuangquan/mkc/gateway/internal/model"
	"github.com/zhushuangquan/mkc/gateway/internal/repository"
	apperrors "github.com/zhushuangquan/mkc/gateway/pkg/errors"
	"github.com/zhushuangquan/mkc/gateway/pkg/jwt"
	"github.com/zhushuangquan/mkc/gateway/pkg/password"
)

// RegisterRequest represents a user registration request.
type RegisterRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required,min=8"`
	Nickname string `json:"nickname"`
}

// LoginRequest represents a user login request.
type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

// RefreshRequest represents a token refresh request.
type RefreshRequest struct {
	RefreshToken string `json:"refresh_token" binding:"required"`
}

// LogoutRequest represents a logout request.
type LogoutRequest struct {
	RefreshToken string `json:"refresh_token" binding:"required"`
}

// AuthResponse is returned on successful register or login.
type AuthResponse struct {
	UserID       string `json:"user_id"`
	Email        string `json:"email"`
	Nickname     string `json:"nickname"`
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	ExpiresIn    int    `json:"expires_in"`
	TokenType    string `json:"token_type"`
}

// RefreshResponse is returned on successful token refresh.
type RefreshResponse struct {
	AccessToken string `json:"access_token"`
	ExpiresIn   int    `json:"expires_in"`
	TokenType   string `json:"token_type"`
}

// UserProfile represents the current authenticated user.
type UserProfile struct {
	UserID   string `json:"user_id"`
	Email    string `json:"email"`
	Nickname string `json:"nickname"`
}

// AuthService defines user authentication operations.
type AuthService interface {
	Register(ctx context.Context, req RegisterRequest) (*AuthResponse, error)
	Login(ctx context.Context, req LoginRequest) (*AuthResponse, error)
	Refresh(ctx context.Context, refreshToken string) (*RefreshResponse, error)
	Logout(ctx context.Context, userUUID, refreshToken string) error
	Me(ctx context.Context, userUUID string) (*UserProfile, error)
}

// PasswordHasher abstracts password hashing and verification.
type PasswordHasher interface {
	Hash(pwd string) (string, error)
	Check(pwd, hash string) bool
}

// BcryptHasher wraps the password package for production use.
type BcryptHasher struct{}

func (BcryptHasher) Hash(pwd string) (string, error) {
	return password.Hash(pwd)
}

func (BcryptHasher) Check(pwd, hash string) bool {
	return password.Check(pwd, hash)
}

// authService is the concrete AuthService implementation.
type authService struct {
	userRepo   repository.UserRepository
	tokenStore repository.TokenStore
	jwtMgr     *jwt.Manager
	hasher     PasswordHasher
}

// NewAuthService creates an AuthService.
func NewAuthService(userRepo repository.UserRepository, tokenStore repository.TokenStore, jwtMgr *jwt.Manager, hasher PasswordHasher) AuthService {
	return &authService{
		userRepo:   userRepo,
		tokenStore: tokenStore,
		jwtMgr:     jwtMgr,
		hasher:     hasher,
	}
}

var (
	passwordMinLen   = 8
	passwordRegexp   = regexp.MustCompile(`[A-Za-z].*[0-9]|[0-9].*[A-Za-z]`)
	emailRegexp      = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
)

func validateRegisterRequest(req RegisterRequest) error {
	if req.Email == "" || !emailRegexp.MatchString(req.Email) {
		return apperrors.BadRequest("VALIDATION_ERROR: invalid email")
	}
	if err := validatePassword(req.Password); err != nil {
		return err
	}
	return nil
}

func validatePassword(p string) error {
	if len(p) < passwordMinLen {
		return apperrors.BadRequest("password must be at least 8 characters")
	}
	if !passwordRegexp.MatchString(p) {
		return apperrors.BadRequest("password must contain both letters and numbers")
	}
	return nil
}

func (s *authService) Register(ctx context.Context, req RegisterRequest) (*AuthResponse, error) {
	if err := validateRegisterRequest(req); err != nil {
		return nil, err
	}

	hash, err := s.hasher.Hash(req.Password)
	if err != nil {
		return nil, apperrors.Internal(fmt.Sprintf("failed to hash password: %v", err))
	}

	user := &model.User{
		UUID:         uuid.NewString(),
		Email:        req.Email,
		PasswordHash: hash,
		Nickname:     req.Nickname,
		Status:       1,
	}

	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, err
	}

	pair, err := s.generateTokenPair(ctx, user)
	if err != nil {
		return nil, err
	}

	return &AuthResponse{
		UserID:       user.UUID,
		Email:        user.Email,
		Nickname:     user.Nickname,
		AccessToken:  pair.AccessToken,
		RefreshToken: pair.RefreshToken,
		ExpiresIn:    pair.ExpiresIn,
		TokenType:    pair.TokenType,
	}, nil
}

func (s *authService) Login(ctx context.Context, req LoginRequest) (*AuthResponse, error) {
	user, err := s.userRepo.GetByEmail(ctx, req.Email)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.Unauthorized("AUTH_INVALID_CREDENTIALS: email or password incorrect")
		}
		return nil, apperrors.Internal(fmt.Sprintf("failed to get user: %v", err))
	}

	if !s.hasher.Check(req.Password, user.PasswordHash) {
		return nil, apperrors.Unauthorized("AUTH_INVALID_CREDENTIALS: email or password incorrect")
	}

	pair, err := s.generateTokenPair(ctx, user)
	if err != nil {
		return nil, err
	}

	return &AuthResponse{
		UserID:       user.UUID,
		Email:        user.Email,
		Nickname:     user.Nickname,
		AccessToken:  pair.AccessToken,
		RefreshToken: pair.RefreshToken,
		ExpiresIn:    pair.ExpiresIn,
		TokenType:    pair.TokenType,
	}, nil
}

func (s *authService) Refresh(ctx context.Context, refreshToken string) (*RefreshResponse, error) {
	userUUID, session, err := s.tokenStore.FindByTokenUUID(ctx, refreshToken)
	if err != nil {
		return nil, apperrors.Unauthorized("AUTH_SESSION_EXPIRED: session expired, please login again")
	}

	var rs RefreshSession
	if err := json.Unmarshal(session, &rs); err != nil {
		return nil, apperrors.Unauthorized("AUTH_SESSION_EXPIRED: session expired, please login again")
	}

	user, err := s.userRepo.GetByUUID(ctx, userUUID)
	if err != nil {
		return nil, apperrors.Unauthorized("AUTH_SESSION_EXPIRED: session expired, please login again")
	}

	if err := s.tokenStore.Delete(ctx, userUUID, refreshToken); err != nil {
		return nil, apperrors.Internal(fmt.Sprintf("failed to delete refresh session: %v", err))
	}

	accessToken, err := s.jwtMgr.GenerateAccessToken(user.UUID, user.Email)
	if err != nil {
		return nil, apperrors.Internal(fmt.Sprintf("failed to generate access token: %v", err))
	}

	return &RefreshResponse{
		AccessToken: accessToken,
		ExpiresIn:   int(s.jwtMgr.AccessTTL().Seconds()),
		TokenType:   "Bearer",
	}, nil
}

func (s *authService) Logout(ctx context.Context, userUUID, refreshToken string) error {
	if err := s.tokenStore.Delete(ctx, userUUID, refreshToken); err != nil {
		return apperrors.Internal(fmt.Sprintf("failed to delete refresh session: %v", err))
	}
	return nil
}

func (s *authService) Me(ctx context.Context, userUUID string) (*UserProfile, error) {
	user, err := s.userRepo.GetByUUID(ctx, userUUID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			return nil, apperrors.NotFound("user")
		}
		return nil, apperrors.Internal(fmt.Sprintf("failed to get user: %v", err))
	}

	return &UserProfile{
		UserID:   user.UUID,
		Email:    user.Email,
		Nickname: user.Nickname,
	}, nil
}

type RefreshSession struct {
	UserUUID string `json:"user_uuid"`
	Email    string `json:"email"`
}

type tokenPair struct {
	AccessToken  string
	RefreshToken string
	ExpiresIn    int
	TokenType    string
}

func (s *authService) generateTokenPair(ctx context.Context, user *model.User) (*tokenPair, error) {
	accessToken, err := s.jwtMgr.GenerateAccessToken(user.UUID, user.Email)
	if err != nil {
		return nil, apperrors.Internal(fmt.Sprintf("failed to generate access token: %v", err))
	}

	tokenUUID := uuid.NewString()
	session := RefreshSession{
		UserUUID: user.UUID,
		Email:    user.Email,
	}
	data, err := json.Marshal(session)
	if err != nil {
		return nil, apperrors.Internal(fmt.Sprintf("failed to marshal refresh session: %v", err))
	}

	if err := s.tokenStore.Save(ctx, user.UUID, tokenUUID, data, s.jwtMgr.RefreshTTL()); err != nil {
		return nil, apperrors.Internal(fmt.Sprintf("failed to save refresh session: %v", err))
	}

	return &tokenPair{
		AccessToken:  accessToken,
		RefreshToken: tokenUUID,
		ExpiresIn:    int(s.jwtMgr.AccessTTL().Seconds()),
		TokenType:    "Bearer",
	}, nil
}
