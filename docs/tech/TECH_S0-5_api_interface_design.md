# 技术文档：[S0-5] API 接口设计规范与技术实现

> 版本：v1.0  
> 日期：2026-07-06  > 作者：朱双泉  > 级别：架构师/API 负责人  > 关联 PRD：[PRD_S0-5_api_interface_design.md](../prd/PRD_S0-5_api_interface_design.md)

---

## 1. 文档目标

本文档定义 MKC 项目的 API 设计规范、认证鉴权机制、统一响应格式、错误码体系、OpenAPI 规范、版本控制策略、SSE 流式接口实现要点以及前后端对接细节。

---

## 2. API 设计原则

| 原则 | 说明 |
|---|---|
| RESTful 为主 | 资源导向 URL，HTTP 方法表达操作 |
| 统一响应格式 | 所有接口返回相同 envelope |
| 版本化 URL | `/api/v1/...` 路径中包含版本号 |
| 无状态认证 | JWT access_token + Redis Session refresh_token |
| 错误码明确 | 业务错误码 + HTTP 状态码分离 |
| 可观测 | 统一 trace_id、请求日志、OpenTelemetry |
| 前后端一致 | Swagger/OpenAPI 作为唯一真理源 |

---

## 3. URL 版本控制策略

```
/api/v1/auth/register
/api/v1/resources
/api/v1/tasks/{uuid}
/api/v1/conversations/{uuid}/messages
```

**版本升级规则**：
- 向后兼容的改动：保持 v1
- 破坏性改动：引入 v2，v1 保留至少 6 个月
- 废弃接口通过响应头 `Deprecation` 提醒

---

## 4. 统一响应格式

### 4.1 成功响应

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-07-06T10:00:00Z"
  }
}
```

### 4.2 失败响应

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTH_INVALID_TOKEN",
    "message": "访问令牌已过期或无效"
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-07-06T10:00:00Z"
  }
}
```

### 4.3 分页响应

```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  },
  "error": null,
  "meta": { ... }
}
```

---

## 5. 认证鉴权机制

### 5.1 JWT + Redis Session 混合方案

```
┌─────────┐     login      ┌──────────┐     generate      ┌───────┐
│ Client  │ ─────────────▶ │ Gateway  │ ────────────────▶ │ Redis │
│         │ ◀───────────── │          │ ◀───────────────  │       │
└─────────┘  access_token  │          │  refresh_token    └───────┘
                           └──────────┘
```

**Token 设计**：

| Token | 存储位置 | 有效期 | 用途 |
|---|---|---|---|
| access_token | 客户端内存（Riverpod State） | 15 分钟 | 日常 API 鉴权 |
| refresh_token | Redis + HttpOnly Cookie | 7 天 | 刷新 access_token |

### 5.2 access_token 内容

```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "jti": "token_uuid",
  "iat": 1712345678,
  "exp": 1712346578
}
```

**注意**：access_token 仅包含最小信息，不存权限角色（本项目为单用户/普通用户）。

### 5.3 refresh_token 存储

Redis key：`refresh:{user_uuid}:{token_uuid}`
Value：`user_uuid`
TTL：7 天

### 5.4 认证中间件流程

```go
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        authHeader := c.GetHeader("Authorization")
        if authHeader == "" {
            response.Unauthorized(c, "AUTH_MISSING_TOKEN", "缺少认证信息")
            return
        }

        parts := strings.SplitN(authHeader, " ", 2)
        if len(parts) != 2 || parts[0] != "Bearer" {
            response.Unauthorized(c, "AUTH_INVALID_FORMAT", "认证格式错误")
            return
        }

        claims, err := jwt.Parse(parts[1])
        if err != nil {
            response.Unauthorized(c, "AUTH_INVALID_TOKEN", err.Error())
            return
        }

        c.Set("user_uuid", claims.Subject)
        c.Set("user_email", claims.Email)
        c.Next()
    }
}
```

### 5.5 Token 刷新流程

```
POST /api/v1/auth/refresh
Cookie: refresh_token=xxx

Response:
{
  "success": true,
  "data": {
    "access_token": "new_jwt_token",
    "expires_in": 900
  }
}
```

刷新时旧 refresh_token 作废，生成新 token 对。

---

## 6. 错误码体系

### 6.1 错误码命名规则

`{DOMAIN}_{ERROR_TYPE}`，例如 `AUTH_INVALID_TOKEN`。

### 6.2 错误码表

| 错误码 | HTTP 状态码 | 说明 |
|---|---|---|
| AUTH_MISSING_TOKEN | 401 | 缺少 Token |
| AUTH_INVALID_FORMAT | 401 | Authorization 头格式错误 |
| AUTH_INVALID_TOKEN | 401 | Token 无效或过期 |
| AUTH_REFRESH_TOKEN_INVALID | 401 | Refresh Token 无效 |
| AUTH_EMAIL_EXISTS | 409 | 邮箱已注册 |
| AUTH_INVALID_CREDENTIALS | 401 | 邮箱或密码错误 |
| USER_NOT_FOUND | 404 | 用户不存在 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| RESOURCE_TOO_LARGE | 413 | 文件超过大小限制 |
| RESOURCE_INVALID_TYPE | 400 | 不支持的文件类型 |
| TASK_NOT_FOUND | 404 | 任务不存在 |
| TASK_ALREADY_RUNNING | 409 | 任务已在运行 |
| CONVERSATION_NOT_FOUND | 404 | 会话不存在 |
| VALIDATION_ERROR | 400 | 参数校验失败 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| RATE_LIMIT_EXCEEDED | 429 | 请求过于频繁 |

### 6.3 参数校验错误格式

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      {"field": "email", "message": "邮箱格式不正确"},
      {"field": "password", "message": "密码长度至少 8 位"}
    ]
  },
  "meta": { ... }
}
```

---

## 7. 核心 API 设计

### 7.1 认证接口

```yaml
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
```

### 7.2 资源接口

```yaml
GET    /api/v1/resources          # 列表（分页）
POST   /api/v1/resources          # 创建资源（仅元数据）
GET    /api/v1/resources/{uuid}   # 详情
DELETE /api/v1/resources/{uuid}   # 删除
POST   /api/v1/resources/{uuid}/upload-url  # 获取预签名上传 URL
```

### 7.3 任务接口

```yaml
GET /api/v1/tasks                # 任务列表
GET /api/v1/tasks/{uuid}         # 任务详情
GET /api/v1/tasks/{uuid}/events  # SSE 任务进度推送
```

### 7.4 会话/消息接口

```yaml
GET    /api/v1/conversations
POST   /api/v1/conversations
GET    /api/v1/conversations/{uuid}
DELETE /api/v1/conversations/{uuid}
GET    /api/v1/conversations/{uuid}/messages
POST   /api/v1/conversations/{uuid}/messages      # 普通提问
POST   /api/v1/conversations/{uuid}/messages/stream  # SSE 流式回答
```

---

## 8. OpenAPI 3.0 规范

### 8.1 文件结构

```
docs/api/
├── openapi.yaml          # 主入口
├── paths/
│   ├── auth.yaml
│   ├── resources.yaml
│   ├── tasks.yaml
│   └── conversations.yaml
├── schemas/
│   ├── user.yaml
│   ├── resource.yaml
│   ├── task.yaml
│   └── message.yaml
└── components/
    └── security.yaml
```

### 8.2 使用 swaggo 自动生成 Go 文档

```bash
go install github.com/swaggo/swag/cmd/swag@latest
cd gateway
swag init -g cmd/server/main.go
```

生成 `docs/swagger.json` 和 `docs/swagger.yaml`，通过 `/swagger/index.html` 访问。

### 8.3 最小 OpenAPI 示例

```yaml
openapi: 3.0.0
info:
  title: MKC API
  version: 1.0.0
  description: Multimedia Knowledge Companion API
servers:
  - url: http://mkc.local/api/v1
paths:
  /health:
    get:
      tags: [System]
      summary: 健康检查
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  schemas:
    HealthResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
          properties:
            status:
              type: string
```

---

## 9. SSE 流式接口设计

### 9.1 适用场景

- 任务进度推送（转录、解析、索引）
- AI 问答流式输出

### 9.2 SSE 响应格式

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

id: 1
event: chunk
data: {"content": "你好", "done": false}

id: 2
event: chunk
data: {"content": "，", "done": false}

id: 3
event: done
data: {"content": "", "done": true, "citations": [...]}
```

### 9.3 Gateway SSE 转发

Gateway 使用 `http.Client` 流式读取 ai-service SSE，原样写入 gin ResponseWriter：

```go
func StreamChat(c *gin.Context) {
    req, _ := http.NewRequestWithContext(c.Request.Context(), "POST", aiServiceURL, body)
    resp, err := httpClient.Do(req)
    if err != nil {
        response.Error(c, ...)
        return
    }
    defer resp.Body.Close()

    c.Header("Content-Type", "text/event-stream")
    c.Header("Cache-Control", "no-cache")
    c.Header("Connection", "keep-alive")
    c.Stream(func(w io.Writer) bool {
        buf := make([]byte, 1024)
        n, err := resp.Body.Read(buf)
        if n > 0 {
            w.Write(buf[:n])
        }
        return err == nil
    })
}
```

---

## 10. 限流设计

### 10.1 策略

使用 Redis + Token Bucket 算法：

```
key: rate_limit:{user_uuid}:{path}
capacity: 10
refill_rate: 1/s
```

### 10.2 限流中间件

```go
func RateLimitMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        userUUID := c.GetString("user_uuid")
        allowed, retryAfter := limiter.Allow(c.Request.Context(), userUUID, c.Request.URL.Path)
        if !allowed {
            c.Header("Retry-After", strconv.Itoa(retryAfter))
            response.TooManyRequests(c, "RATE_LIMIT_EXCEEDED", "请求过于频繁")
            return
        }
        c.Next()
    }
}
```

---

## 11. 日志与 Trace

### 11.1 统一请求日志

```json
{
  "level": "info",
  "request_id": "req_abc123",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status": 200,
  "duration_ms": 45,
  "client_ip": "127.0.0.1",
  "user_agent": "...",
  "user_uuid": "..."
}
```

### 11.2 Trace 传播

- Gateway 生成 `trace_id`
- 调用 ai-service 时通过 `X-Trace-ID` 透传
- Jaeger 收集 trace，Zipkin/B3 格式兼容

---

## 12. 检查清单

- [ ] OpenAPI 3.0 文档创建
- [ ] swaggo 集成，/swagger/index.html 可访问
- [ ] 统一响应封装实现
- [ ] 错误码枚举定义
- [ ] JWT + Redis Session 认证流程跑通
- [ ] 限流中间件实现
- [ ] SSE 接口示例可工作
- [ ] API 版本控制策略文档化
- [ ] 前后端字段命名约定统一
