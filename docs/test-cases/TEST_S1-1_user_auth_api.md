# S1-1 测试用例：用户注册/登录 API

## 1. 范围与目标

验证 Gateway 认证模块提供的注册、登录、刷新、登出 API 在功能、安全、异常分支上均符合 PRD/TECH 要求，双 token 机制与 Redis Session 状态一致。

## 2. 测试环境

- Go 1.22+
- MySQL 8 本地容器或 K8s MySQL
- Redis 7 本地容器或 K8s Redis
- `gateway/` 已执行 `go mod tidy` 并编译通过
- 环境变量 `APP_JWT_SECRET` 已配置

## 3. 测试用例

### 3.1 注册接口

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-1-001 | Functional | Integration | P0 | 正常注册返回双 token | 服务运行，Redis/MySQL 可达 | `POST /api/v1/auth/register` 传入合法邮箱/密码 | 返回 200，包含 access_token、refresh_token、expires_in、user_id | PRD AC-1 |
| MKC-TC-S1-1-002 | Functional | Unit | P1 | 密码被 bcrypt 哈希存储 | 注册成功 | 查询 `users.password_hash` | 字段以 `$2a$` 开头，不等于明文 | PRD AC-5 |
| MKC-TC-S1-1-003 | Negative | Integration | P0 | 重复邮箱注册返回 409 | 已存在邮箱 `a@b.com` | 再次用相同邮箱注册 | 返回 409，code=`CONFLICT` | PRD AC-6 |
| MKC-TC-S1-1-004 | Negative | Integration | P0 | 邮箱格式非法返回 400 | 服务运行 | 传入 `email="not-email"` | 返回 400，code=`VALIDATION_ERROR` | PRD AC-1 |
| MKC-TC-S1-1-005 | Negative | Integration | P1 | 密码过短返回 400 | 服务运行 | 传入密码长度 5 | 返回 400，提示密码至少 8 位 | PRD 技术要点 |
| MKC-TC-S1-1-006 | Negative | Integration | P1 | 密码缺少数字或字母返回 400 | 服务运行 | 传入纯数字密码 | 返回 400，提示密码必须包含字母和数字 | PRD 技术要点 |
| MKC-TC-S1-1-007 | Security | Integration | P1 | 注册接口触发频率限制 | 服务运行 | 同一 IP 60 秒内请求 61 次 | 第 61 次返回 429 Too Many Requests | PRD 安全要求 |

### 3.2 登录接口

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-1-008 | Functional | Integration | P0 | 正常登录返回双 token | 用户已注册 | `POST /api/v1/auth/login` | 返回 200，包含双 token 与用户信息 | PRD AC-2 |
| MKC-TC-S1-1-009 | Security | Integration | P0 | 错误密码返回 401 且不提示邮箱是否存在 | 用户已注册 | 使用错误密码登录 | 返回 401，code=`AUTH_INVALID_CREDENTIALS`，message 为统一文案 | PRD 安全要求 |
| MKC-TC-S1-1-010 | Security | Integration | P0 | 不存在邮箱登录返回 401 | 邮箱未注册 | 用未注册邮箱登录 | 返回 401，文案与错误密码一致 | PRD 安全要求 |
| MKC-TC-S1-1-011 | Negative | Integration | P1 | 缺少密码返回 400 | 服务运行 | 请求体只含 email | 返回 400，code=`VALIDATION_ERROR` | PRD AC-2 |
| MKC-TC-S1-1-012 | Functional | Integration | P1 | 同一用户多设备登录产生不同 refresh_token | 用户已注册 | 连续登录两次 | 两个 refresh_token 不同且 Redis 均存在 | PRD 技术要点 |

### 3.3 刷新接口

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-1-013 | Functional | Integration | P0 | 有效 refresh_token 换取 access_token | 已登录 | `POST /api/v1/auth/refresh` | 返回 200，新 access_token 可解析出相同用户 | PRD AC-3 |
| MKC-TC-S1-1-014 | Security | Integration | P0 | 使用过期 refresh_token 返回 401 | token 已过期 | 调用 refresh | 返回 401，code=`AUTH_SESSION_EXPIRED` | PRD AC-3 |
| MKC-TC-S1-1-015 | Security | Integration | P1 | refresh_token 只能使用一次 | 已登录 | 用同一 refresh_token 刷新两次 | 第二次返回 401 | PRD 技术要点 |
| MKC-TC-S1-1-016 | Negative | Integration | P1 | 非法格式 refresh_token 返回 401 | 服务运行 | 传入空字符串 | 返回 401 | PRD AC-3 |

### 3.4 登出接口

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-1-017 | Functional | Integration | P0 | 登出后 refresh_token 失效 | 已登录 | `POST /api/v1/auth/logout` 带 access_token | 返回 200；原 refresh_token 刷新返回 401 | PRD AC-4 |
| MKC-TC-S1-1-018 | Security | Integration | P0 | 缺失 Authorization 返回 401 | 服务运行 | 不带 token 调用 logout | 返回 401 | PRD AC-4 |
| MKC-TC-S1-1-019 | Security | Integration | P1 | 使用无效 access_token 登出返回 401 | 服务运行 | 传入伪造 token | 返回 401 | PRD AC-4 |

### 3.5 JWT 鉴权中间件

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-1-020 | Functional | Unit | P0 | 合法 access_token 通过中间件 | 已登录 | 携带 Bearer token 访问受保护路由 | 进入 handler，context 中存在 user_uuid | TECH 5.4 |
| MKC-TC-S1-1-021 | Security | Unit | P0 | 过期 access_token 被拦截 | token 过期 | 访问受保护路由 | 返回 401 | TECH 5.4 |
| MKC-TC-S1-1-022 | Security | Unit | P1 | 错误签名的 token 被拦截 | 服务运行 | 携带篡改 token | 返回 401 | TECH 5.4 |
| MKC-TC-S1-1-023 | Security | Unit | P1 | 缺少 Authorization 被拦截 | 服务运行 | 不带 token | 返回 401 | TECH 5.4 |

### 3.6 数据一致性与代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-1-024 | Functional | Static | P1 | 无硬编码密钥 | 代码存在 | 搜索 `jwt_secret`、`password` 硬编码 | 无真实密钥 | 安全基线 |
| MKC-TC-S1-1-025 | Functional | Integration | P1 | 测试覆盖率 80%+ | 测试存在 | `go test -cover ./internal/service/... ./internal/handler/...` | 覆盖率 ≥80% | PRD AC-9 |
| MKC-TC-S1-1-026 | Functional | Integration | P1 | race detector 通过 | 测试存在 | `go test -race ./...` | 无 data race | Go Testing 规范 |
| MKC-TC-S1-1-027 | Idempotency | Integration | P2 | 重复注册返回一致 409 | 服务运行 | 同一请求连续注册 3 次 | 均返回 409 | 工程最佳实践 |

## 4. 测试执行清单

- [ ] 注册接口正常与异常分支
- [ ] 登录接口正常与异常分支
- [ ] 刷新接口正常与一次性使用
- [ ] 登出接口与 refresh_token 失效验证
- [ ] JWT 中间件保护受保护路由
- [ ] 数据库唯一索引触发 409
- [ ] Redis refresh key TTL 与删除验证
- [ ] `go test ./...` 通过且覆盖率 80%+
- [ ] `go test -race ./...` 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
