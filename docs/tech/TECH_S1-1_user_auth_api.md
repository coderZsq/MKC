# 技术文档：[S1-1] 用户注册/登录 API 设计

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 级别：后端工程师  
> 关联 PRD：[PRD_S1-1_user_auth_api.md](../prd/PRD_S1-1_user_auth_api.md)

---

## 1. 文档目标

定义 MKC Gateway 用户认证模块的接口契约、数据流、模块划分与关键代码实现，为 S1-1 编码提供可直接落地的蓝图。

---

## 2. 技术栈

- Go 1.22+
- Gin 1.10.x
- GORM 1.25.x
- MySQL 8 / Redis 7
- golang-jwt/jwt/v5
- bcrypt

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 否 | 用户注册 |
| POST | `/api/v1/auth/login` | 否 | 用户登录 |
| POST | `/api/v1/auth/refresh` | 否（需 refresh_token） | 刷新 access_token |
| POST | `/api/v1/auth/logout` | 是 | 用户登出 |
| GET | `/api/v1/auth/me` | 是 | 获取当前用户信息（可选） |

### 3.1 请求/响应示例

**POST /api/v1/auth/register**

```json
// Request
{
  "email": "user@example.com",
  "password": "Passw0rd!",
  "nickname": "Alice"
}

// Response 200
{
  "success": true,
  "data": {
    "user_id": "01922b9a-...",
    "email": "user@example.com",
    "nickname": "Alice",
    "access_token": "eyJhbG...",
    "refresh_token": "550e8400-e29b-41d4-a716-446655440000",
    "expires_in": 900,
    "token_type": "Bearer"
  },
  "error": null,
  "meta": { "request_id": "...", "timestamp": "2026-07-08T10:00:00Z" }
}
```

**POST /api/v1/auth/login**

```json
// Request
{
  "email": "user@example.com",
  "password": "Passw0rd!"
}

// Response 200
{
  "success": true,
  "data": { ... }
}
```

**POST /api/v1/auth/refresh**

```json
// Request
{ "refresh_token": "550e8400-..." }

// Response 200
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...",
    "expires_in": 900,
    "token_type": "Bearer"
  }
}
```

**POST /api/v1/auth/logout**

```text
Authorization: Bearer <access_token>
```

```json
// Response 200
{
  "success": true,
  "data": null,
  "error": null,
  "meta": { "request_id": "..." }
}
```

---

## 4. 数据模型

复用 `gateway/internal/model/user.go`：

```go
type User struct {
    ID           uint64
    UUID         string         `gorm:"uniqueIndex:uk_users_uuid"`
    Email        string         `gorm:"uniqueIndex:uk_users_email"`
    PasswordHash string
    Nickname     string
    AvatarURL    string
    Status       uint8
    CreatedAt    time.Time
    UpdatedAt    time.Time
    DeletedAt    gorm.DeletedAt
}
```

Redis key 规范：

```text
refresh:{user_uuid}:{token_uuid} -> { "user_uuid": "...", "email": "..." }
TTL: 7 * 24 * 3600 seconds
```

---

## 5. 模块设计

### 5.1 Repository 层

```go
type UserRepository interface {
    Create(ctx context.Context, user *model.User) error
    GetByEmail(ctx context.Context, email string) (*model.User, error)
    GetByUUID(ctx context.Context, uuid string) (*model.User, error)
}
```

- `Create` 使用 GORM `Create`，捕获 `mysql.ErrDuplicateEntry` 后返回 `apperrors.Conflict("email already exists")`。
- `GetByEmail` 用于登录查询，即使邮箱不存在也返回统一错误，避免邮箱枚举。

### 5.2 Service 层

```go
type AuthService interface {
    Register(ctx context.Context, req RegisterRequest) (*TokenPair, error)
    Login(ctx context.Context, req LoginRequest) (*TokenPair, error)
    Refresh(ctx context.Context, refreshToken string) (*AccessToken, error)
    Logout(ctx context.Context, userUUID, tokenUUID string) error
    Me(ctx context.Context, userUUID string) (*UserProfile, error)
}
```

- `Register`：校验输入 → bcrypt 哈希 → 生成 UUID → 写入 DB → 签发双 token → 写入 Redis。
- `Login`：按邮箱查用户 → bcrypt 校验 → 签发双 token → 写入 Redis。
- `Refresh`：解析 token_uuid → Redis 查 key → 验证归属 → 删除旧 key → 签发新 access_token（新 refresh_token 可选）。
- `Logout`：从当前 access_token 解析 user_uuid，从请求体或 Redis scan 定位 token_uuid 并删除。

### 5.3 Handler 层

```go
type AuthHandler struct {
    svc AuthService
}

func (h *AuthHandler) Register(c *gin.Context) {
    var req RegisterRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        response.BadRequest(c, "VALIDATION_ERROR", err.Error())
        return
    }
    pair, err := h.svc.Register(c.Request.Context(), req)
    if err != nil {
        handleServiceError(c, err)
        return
    }
    response.OK(c, pair)
}
```

### 5.4 JWT 鉴权中间件

```go
func JWTAuth(jwtMgr *jwt.Manager) gin.HandlerFunc {
    return func(c *gin.Context) {
        header := c.GetHeader("Authorization")
        token := strings.TrimPrefix(header, "Bearer ")
        claims, err := jwtMgr.ParseAccessToken(token)
        if err != nil {
            response.Unauthorized(c, "AUTH_INVALID_TOKEN", "访问令牌无效或已过期")
            c.Abort()
            return
        }
        c.Set("user_uuid", claims.Subject)
        c.Set("email", claims.Email)
        c.Next()
    }
}
```

---

## 6. 关键代码实现

### 6.1 Token 对生成

```go
func (s *authService) generateTokenPair(user *model.User) (*TokenPair, error) {
    accessToken, err := s.jwtMgr.GenerateAccessToken(user.UUID, user.Email)
    if err != nil {
        return nil, fmt.Errorf("generate access token: %w", err)
    }

    tokenUUID := uuid.NewString()
    key := fmt.Sprintf("refresh:%s:%s", user.UUID, tokenUUID)
    session := &RefreshSession{
        UserUUID: user.UUID,
        Email:    user.Email,
    }
    data, _ := json.Marshal(session)
    if err := s.redis.Set(c.Request.Context(), key, data, s.jwtMgr.RefreshTTL()).Err(); err != nil {
        return nil, fmt.Errorf("save refresh session: %w", err)
    }

    return &TokenPair{
        AccessToken:  accessToken,
        RefreshToken: tokenUUID,
        ExpiresIn:    int(s.jwtMgr.AccessTTL().Seconds()),
        TokenType:    "Bearer",
    }, nil
}
```

### 6.2 密码校验策略

```go
var (
    passwordMinLen = 8
    passwordRegexp = regexp.MustCompile(`[A-Za-z].*[0-9]|[0-9].*[A-Za-z]`)
)

func validatePassword(p string) error {
    if len(p) < passwordMinLen {
        return apperrors.BadRequest("password must be at least 8 characters")
    }
    if !passwordRegexp.MatchString(p) {
        return apperrors.BadRequest("password must contain both letters and numbers")
    }
    return nil
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 参数校验失败 | 400 | VALIDATION_ERROR | 请求参数错误 |
| 邮箱已注册 | 409 | CONFLICT | 邮箱已被注册 |
| 登录凭据错误 | 401 | AUTH_INVALID_CREDENTIALS | 邮箱或密码错误 |
| access_token 无效 | 401 | AUTH_INVALID_TOKEN | 访问令牌无效或已过期 |
| refresh_token 无效 | 401 | AUTH_SESSION_EXPIRED | 会话已过期，请重新登录 |
| Redis 写入失败 | 500 | INTERNAL_ERROR | 服务器内部错误 |

---

## 8. Web 端适配要点

- Gateway 注册/登录/刷新/登出接口需启用 CORS，允许 Flutter Web 启动域名、允许 `Content-Type: application/json` 与 `Authorization` 头。
- Web 端 Flutter 通过 Dio 以 JSON 形式调用；错误响应统一使用 envelope，不在浏览器控制台暴露堆栈。
- Web 端 Widget 与集成测试使用 `flutter test --platform chrome` 与 ChromeDriver。

---

## 9. 测试策略

- **单元测试**：service 逻辑、bcrypt 校验、JWT 签发/解析
- **集成测试**：repository + SQLite/MySQL + Redis 容器，验证注册/登录/刷新/登出完整流程
- **接口测试**：httptest 模拟 handler，覆盖 400/401/409 等分支

---

## 10. 检查清单

- [ ] `AuthHandler` 注册/登录/刷新/登出接口实现
- [ ] `AuthService` 业务逻辑与双 token 管理实现
- [ ] `UserRepository` 数据访问实现
- [ ] `JWTAuth` 中间件注册到受保护路由
- [ ] 密码 bcrypt 哈希与校验
- [ ] Redis refresh_token Session 写入/删除
- [ ] 输入校验与统一错误响应
- [ ] 单元/集成测试覆盖率 80%+
- [ ] Swagger / OpenAPI 文档同步更新
