# 技术文档：[S0-7] Go Gateway 服务骨架与架构设计

> 版本：v1.0  
> 日期：2026-07-06  > 作者：朱双泉  > 级别：架构师/后端负责人  > 关联 PRD：[PRD_S0-7_go_gateway_skeleton.md](../prd/PRD_S0-7_go_gateway_skeleton.md)

---

## 1. 文档目标

本文档定义 MKC 项目 Go Gateway 服务的架构设计、分层结构、依赖选择、配置管理、数据库连接、Redis 连接、JWT 实现、中间件设计、错误处理、日志记录、健康检查、Dockerfile 以及 K8s 部署初稿。

---

## 2. 技术栈

| 依赖 | 版本 | 用途 |
|---|---|---|
| Gin | 1.10+ | Web 框架 |
| GORM | 1.25+ | ORM |
| go-redis | 9.5+ | Redis 客户端 |
| Viper | 1.19+ | 配置管理 |
| jwt-go / golang-jwt | 5.x | JWT 实现 |
| bcrypt | 标准库 | 密码哈希 |
| zap | 1.27+ | 结构化日志 |
| swaggo | 1.16+ | Swagger 文档 |
| opentelemetry-go | 1.27+ | 可观测性 |
| testify | 1.9+ | 单元测试 |

---

## 3. 项目分层

```
gateway/
├── cmd/server/            # 程序入口
│   └── main.go
├── internal/              # 私有代码
│   ├── config/            # 配置结构体与加载
│   ├── handler/           # HTTP handler
│   ├── middleware/        # Gin 中间件
│   ├── model/             # GORM 模型
│   ├── repository/        # 数据访问层
│   ├── router/            # 路由注册
│   └── service/           # 业务逻辑层
├── pkg/                   # 可复用包
│   ├── response/          # 统一响应
│   ├── errors/            # 错误定义
│   ├── jwt/               # JWT 工具
│   └── utils/             # 通用工具
├── migrations/            # 数据库迁移
├── config/                # 配置文件
│   ├── config.yaml
│   └── config.example.yaml
├── scripts/               # 脚本
├── Dockerfile
├── Makefile
└── README.md
```

---

## 4. 应用启动流程

```
main.go
  │
  ├── 加载配置 (Viper)
  │
  ├── 初始化 Logger (zap)
  │
  ├── 连接 MySQL (GORM)
  │
  ├── 连接 Redis (go-redis)
  │
  ├── 执行 AutoMigrate
  │
  ├── 注册 Repositories
  │
  ├── 注册 Services
  │
  ├── 注册 Handlers
  │
  ├── 初始化 Router
  │
  └── 启动 HTTP Server
```

---

## 5. 配置管理

### 5.1 配置结构

```yaml
app:
  name: mkc-gateway
  version: 0.1.0
  env: dev
  port: 8080

log:
  level: info
  format: json

mysql:
  host: mysql
  port: 3306
  user: mkc
  password: ""
  dbname: mkc
  max_open_conns: 25
  max_idle_conns: 5
  conn_max_lifetime: 30m

redis:
  addr: redis:6379
  password: ""
  db: 0
  pool_size: 10

jwt:
  secret: "change-me-in-prod"
  access_ttl: 15m
  refresh_ttl: 168h

ai_service:
  base_url: http://ai-service:5000
  timeout: 60s
```

### 5.2 Viper 加载

```go
package config

import (
    "github.com/spf13/viper"
)

type Config struct {
    App        AppConfig        `mapstructure:"app"`
    Log        LogConfig        `mapstructure:"log"`
    MySQL      MySQLConfig      `mapstructure:"mysql"`
    Redis      RedisConfig      `mapstructure:"redis"`
    JWT        JWTConfig        `mapstructure:"jwt"`
    AIService  AIServiceConfig  `mapstructure:"ai_service"`
}

func Load(path string) (*Config, error) {
    viper.SetConfigFile(path)
    viper.AutomaticEnv()

    if err := viper.ReadInConfig(); err != nil {
        return nil, err
    }

    var cfg Config
    if err := viper.Unmarshal(&cfg); err != nil {
        return nil, err
    }

    return &cfg, nil
}
```

---

## 6. 数据库连接

```go
package repository

import (
    "fmt"
    "gorm.io/driver/mysql"
    "gorm.io/gorm"
)

func NewMySQL(cfg config.MySQLConfig) (*gorm.DB, error) {
    dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
        cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.DBName)

    db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
        Logger: logger.Default.LogMode(logger.Info),
    })
    if err != nil {
        return nil, err
    }

    sqlDB, err := db.DB()
    if err != nil {
        return nil, err
    }

    sqlDB.SetMaxOpenConns(cfg.MaxOpenConns)
    sqlDB.SetMaxIdleConns(cfg.MaxIdleConns)
    sqlDB.SetConnMaxLifetime(cfg.ConnMaxLifetime)

    return db, nil
}
```

---

## 7. JWT 实现

### 7.1 Token 生成与解析

```go
package jwt

import (
    "time"
    "github.com/golang-jwt/jwt/v5"
    "github.com/google/uuid"
)

type Claims struct {
    Email string `json:"email"`
    jwt.RegisteredClaims
}

type Manager struct {
    secret    []byte
    accessTTL time.Duration
    refreshTTL time.Duration
}

func (m *Manager) GenerateAccessToken(userUUID, email string) (string, error) {
    claims := Claims{
        Email: email,
        RegisteredClaims: jwt.RegisteredClaims{
            Subject:   userUUID,
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(m.accessTTL)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
            ID:        uuid.New().String(),
        },
    }
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(m.secret)
}
```

### 7.2 refresh_token 存储

```go
func (r *RedisSessionRepository) StoreRefreshToken(ctx context.Context, tokenUUID, userUUID string, ttl time.Duration) error {
    key := fmt.Sprintf("refresh:%s:%s", userUUID, tokenUUID)
    return r.client.Set(ctx, key, userUUID, ttl).Err()
}

func (r *RedisSessionRepository) ValidateRefreshToken(ctx context.Context, tokenUUID, userUUID string) (bool, error) {
    key := fmt.Sprintf("refresh:%s:%s", userUUID, tokenUUID)
    val, err := r.client.Get(ctx, key).Result()
    if err == redis.Nil {
        return false, nil
    }
    if err != nil {
        return false, err
    }
    return val == userUUID, nil
}
```

---

## 8. 中间件设计

### 8.1 中间件清单

| 中间件 | 用途 |
|---|---|
| RequestID | 生成/透传 trace_id |
| Logger | 请求日志 |
| Recovery | Panic 恢复 |
| CORS | 跨域处理 |
| Auth | JWT 鉴权 |
| RateLimit | 限流 |

### 8.2 Recovery 中间件

```go
func Recovery(logger *zap.Logger) gin.HandlerFunc {
    return func(c *gin.Context) {
        defer func() {
            if err := recover(); err != nil {
                logger.Error("panic recovered",
                    zap.Any("error", err),
                    zap.String("path", c.Request.URL.Path),
                )
                response.InternalError(c)
            }
        }()
        c.Next()
    }
}
```

### 8.3 CORS 中间件

```go
func CORS() gin.HandlerFunc {
    return cors.New(cors.Config{
        AllowOrigins:     []string{"http://localhost:*"},
        AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
        AllowHeaders:     []string{"Authorization", "Content-Type", "X-Request-ID"},
        ExposeHeaders:    []string{"X-Request-ID"},
        AllowCredentials: true,
        MaxAge:           12 * time.Hour,
    })
}
```

---

## 9. 统一响应与错误处理

### 9.1 Response 包

```go
package response

import (
    "github.com/gin-gonic/gin"
    "net/http"
)

type Envelope struct {
    Success bool        `json:"success"`
    Data    interface{} `json:"data"`
    Error   *ErrorInfo  `json:"error"`
    Meta    *MetaInfo   `json:"meta"`
}

type ErrorInfo struct {
    Code    string            `json:"code"`
    Message string            `json:"message"`
    Details map[string]string `json:"details,omitempty"`
}

type MetaInfo struct {
    RequestID string    `json:"request_id"`
    Timestamp time.Time `json:"timestamp"`
}

func OK(c *gin.Context, data interface{}) {
    c.JSON(http.StatusOK, Envelope{
        Success: true,
        Data:    data,
        Meta:    buildMeta(c),
    })
}

func Error(c *gin.Context, status int, code, message string) {
    c.JSON(status, Envelope{
        Success: false,
        Error:   &ErrorInfo{Code: code, Message: message},
        Meta:    buildMeta(c),
    })
}
```

### 9.2 全局错误处理

```go
func ErrorHandler() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Next()

        if len(c.Errors) == 0 {
            return
        }

        err := c.Errors.Last().Err
        var appErr *apperrors.AppError
        if errors.As(err, &appErr) {
            response.Error(c, appErr.Status, appErr.Code, appErr.Message)
            return
        }

        response.InternalError(c)
    }
}
```

---

## 10. 日志设计

### 10.1 zap 初始化

```go
func NewLogger(level, format string) (*zap.Logger, error) {
    cfg := zap.NewProductionConfig()
    if format == "console" {
        cfg = zap.NewDevelopmentConfig()
    }

    lvl, err := zap.ParseAtomicLevel(level)
    if err != nil {
        return nil, err
    }
    cfg.Level = lvl

    return cfg.Build()
}
```

### 10.2 请求日志中间件

```go
func RequestLogger(logger *zap.Logger) gin.HandlerFunc {
    return func(c *gin.Context) {
        start := time.Now()
        c.Next()

        logger.Info("http request",
            zap.String("method", c.Request.Method),
            zap.String("path", c.Request.URL.Path),
            zap.Int("status", c.Writer.Status()),
            zap.Duration("duration", time.Since(start)),
            zap.String("client_ip", c.ClientIP()),
            zap.String("request_id", c.GetString("request_id")),
        )
    }
}
```

---

## 11. 健康检查

```go
func (h *HealthHandler) Health(c *gin.Context) {
    status := map[string]interface{}{
        "status": "ok",
        "version": h.cfg.App.Version,
        "dependencies": map[string]string{
            "mysql": "ok",
            "redis": "ok",
        },
    }

    mysqlOK := h.db.Exec("SELECT 1").Error == nil
    redisOK := h.redis.Ping(c.Request.Context()).Err() == nil

    if !mysqlOK || !redisOK {
        status["status"] = "degraded"
        status["dependencies"]["mysql"] = ternary(mysqlOK, "ok", "down")
        status["dependencies"]["redis"] = ternary(redisOK, "ok", "down")
        c.JSON(http.StatusServiceUnavailable, status)
        return
    }

    c.JSON(http.StatusOK, status)
}
```

---

## 12. Dockerfile

```dockerfile
# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/server

# Runtime stage
FROM alpine:3.19
WORKDIR /app
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/server .
COPY --from=builder /app/config/config.example.yaml ./config/config.yaml
EXPOSE 8080
CMD ["./server"]
```

---

## 13. K8s Deployment 初稿

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  namespace: mkc-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
        - name: gateway
          image: mkc-gateway:latest
          ports:
            - containerPort: 8080
          env:
            - name: CONFIG_PATH
              value: /app/config/config.yaml
          volumeMounts:
            - name: config
              mountPath: /app/config
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
      volumes:
        - name: config
          configMap:
            name: gateway-config
---
apiVersion: v1
kind: Service
metadata:
  name: gateway
  namespace: mkc-dev
spec:
  selector:
    app: gateway
  ports:
    - port: 80
      targetPort: 8080
```

---

## 14. 检查清单

- [ ] `go.mod` 初始化，依赖版本锁定
- [ ] Viper 配置加载完成
- [ ] GORM 连接 MySQL 成功
- [ ] go-redis 连接 Redis 成功
- [ ] JWT 生成/解析实现
- [ ] 统一响应 + 错误码定义
- [ ] 健康检查接口可访问
- [ ] Swagger 文档初始化
- [ ] Dockerfile 构建成功
- [ ] K8s deployment manifest 编写完成
- [ ] 单元测试覆盖核心工具函数
