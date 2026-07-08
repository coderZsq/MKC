# PRD：[S1-1] 实现用户注册/登录 API

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](../AGILE_plan_multimedia_knowledge_assistant.md)、[TECH_S1-1_user_auth_api.md](../tech/TECH_S1-1_user_auth_api.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S1-1 |
| **任务名称** | 实现用户注册/登录 API |
| **所属史诗** | E1 用户认证 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S0-4 数据库 Schema、S0-7 Go Gateway 骨架、S0-5 API 接口文档 |
| **目标 Sprint** | Sprint 1 |

---

## 描述

作为用户，我需要注册和登录系统，以便安全访问我的知识库。本任务在 `gateway/` 中实现一套无状态 JWT access_token + Redis Session refresh_token 的认证 API，为 Flutter 客户端、任务系统、文件上传等后续功能提供统一的身份凭证。

---

## 验收标准（AC）

- [ ] **AC-1** `POST /api/v1/auth/register` 校验邮箱/密码后创建用户，返回 access_token、refresh_token 与用户信息
- [ ] **AC-2** `POST /api/v1/auth/login` 校验邮箱与 bcrypt 密码哈希，登录成功后返回双 token
- [ ] **AC-3** `POST /api/v1/auth/refresh` 用有效 refresh_token 换取新的 access_token
- [ ] **AC-4** `POST /api/v1/auth/logout` 在 Redis 中吊销当前 refresh_token，access_token 在客户端丢弃
- [ ] **AC-5** 密码使用 bcrypt 哈希存储，数据库中不存明文
- [ ] **AC-6** 邮箱唯一性校验，重复注册返回 `409 CONFLICT`
- [ ] **AC-7** access_token 有效期 15 分钟，refresh_token 有效期 7 天
- [ ] **AC-8** 所有错误返回统一 envelope，不暴露内部堆栈
- [ ] **AC-9** 单元测试覆盖率 80%+，包含正常流程与异常分支

---

## 推荐目录结构

```
gateway/
├── internal/
│   ├── handler/
│   │   └── auth_handler.go          # HTTP handler
│   ├── service/
│   │   └── auth_service.go          # 业务逻辑
│   ├── repository/
│   │   └── user_repository.go       # 数据访问
│   ├── model/
│   │   └── user.go                  # 已存在，复用
│   └── middleware/
│       └── auth.go                  # JWT 鉴权中间件
├── pkg/
│   ├── jwt/
│   │   └── manager.go               # 已存在，复用
│   ├── password/
│   │   └── password.go              # 已存在，复用
│   └── response/
│       └── response.go              # 已存在，复用
└── cmd/server/main.go               # 注入 auth handler/service
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| golang-jwt/jwt/v5 | v5.x | JWT 签名与解析 |
| golang.org/x/crypto/bcrypt | 最新 | 密码哈希 |
| go-redis/redis | v9.x | refresh_token Session 存储 |
| gin-gonic/gin | v1.10.x | HTTP 路由与参数绑定 |
| google/uuid | v1.x | token_uuid / user_uuid 生成 |

---

## 技术要点

### 双 Token 策略

- **access_token**：短期 JWT（15 分钟），Gateway 无状态校验，用于保护业务接口。
- **refresh_token**：随机字符串（UUID），有效期 7 天，以 `refresh:{user_uuid}:{token_uuid}` 为 key 写入 Redis，支持登出吊销与多设备管理。

### 安全要求

- 密码最小长度 8 位，必须同时包含字母与数字
- 登录失败时统一返回 `AUTH_INVALID_CREDENTIALS`，避免枚举邮箱是否存在
- refresh_token 只能使用一次，刷新后旧 refresh_token 立即失效
- 所有认证接口开启请求频率限制（每 IP 每端点 60 次/分钟）

### 数据库约束

- `users.email` 已设置唯一索引，重复注册由数据库唯一冲突触发业务错误
- `users.password_hash` 存储 bcrypt 结果，成本因子使用默认值

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Redis 未就绪导致 refresh_token 无法写入 | 注册/登录失败 | 启动时检查 Redis 连接；健康检查中暴露 Redis 状态 |
| JWT secret 未配置 | 服务无法签名 token | 启动时校验 `jwt.secret` 非空，缺失则 `log.Fatal` |
| bcrypt 默认 cost 在测试中过慢 | 单测耗时增加 | 测试环境使用 `bcrypt.MinCost` 或 mock password 包 |

---

## Web 端适配

- Web 端 Flutter 登录/注册使用 Dio 发送 JSON 请求，Gateway 需配置 CORS：允许 Flutter Web 启动域名、允许 `Content-Type: application/json`、允许携带 `Authorization` 头或 credentials。
- 认证接口的错误响应同样返回统一 envelope，避免在浏览器控制台泄露堆栈。
- Web 端 Widget/集成测试使用 `flutter test --platform chrome` 与 ChromeDriver 验证登录/注册流程。

---

## 备注

- 本任务不实现 OAuth / 短信登录等第三方认证
- `/api/v1/auth/me` 可随本卡实现，也可延后到 S1-2 联调时补充
- 账号状态（status）字段预留，默认 `1` 表示正常，`0` 表示禁用；Sprint 1 不实现禁用逻辑
