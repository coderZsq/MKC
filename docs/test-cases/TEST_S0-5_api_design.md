# S0-5 测试用例：API 接口设计

## 1. 范围与目标

验证 OpenAPI 3.0 规范文档、统一响应信封、HTTP 状态码与业务错误码、JWT + Redis refresh_token 认证设计、路径与字段命名规范符合 PRD/TECH 要求，可作为前后端联调契约。

## 2. 测试环境

- `docs/api/openapi.yaml` 已存在
- 可选：`swagger-codegen-cli`、`openapi-generator-cli` 或 `schemathesis` 进行契约校验
- Gateway 已启动并挂载 Swagger UI（可选）

## 3. 测试用例

### 3.1 OpenAPI 规范基础

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-001 | Functional | Static | P0 | `docs/api/openapi.yaml` 存在 | 仓库已克隆 | `ls docs/api/openapi.yaml` | 文件存在 | PRD AC-1 |
| MKC-TC-S0-5-002 | Functional | Static | P0 | OpenAPI 文件语法版本为 3.0.x | 文件存在 | 读取 `openapi` 字段 | 值为 `3.0.0` 或 `3.0.3` | PRD 技术要点 |
| MKC-TC-S0-5-003 | Functional | Contract | P0 | OpenAPI 文件通过 schema 校验 | 文件存在 | `swagger-codegen-cli validate -i docs/api/openapi.yaml` | 无 ERROR，允许 WARNING | PRD AC-1 |
| MKC-TC-S0-5-004 | Functional | Static | P1 | `docs/api/api-design.md` 存在 | 仓库已克隆 | `ls docs/api/api-design.md` | 文件存在 | PRD 文件位置 |
| MKC-TC-S0-5-005 | Functional | Static | P1 | API base path 为 `/api/v1/` | 文件存在 | `grep "servers\|basePath" docs/api/openapi.yaml` | 基础路径包含 `/api/v1/` | PRD 技术要点 |

### 3.2 统一响应信封

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-006 | Functional | Contract | P0 | 成功响应包含 `success`、`data`、`error`、`meta` | 存在响应定义 | 检查每个端点的 success response schema | 四字段均存在，`success` 为 boolean | PRD AC-2 |
| MKC-TC-S0-5-007 | Functional | Contract | P0 | 错误响应包含 `success`、`data`、`error`、`meta` | 存在响应定义 | 检查 error response schema | 四字段均存在，`success=false`，`error` 包含 `code` 与 `message` | PRD 错误响应 |
| MKC-TC-S0-5-008 | Functional | Contract | P1 | 分页响应 `meta` 包含 page / limit / total | 列表接口定义存在 | 检查 `GET /api/v1/tasks` 响应 schema | `meta` 包含 `page`、`limit`、`total` | PRD 分页响应 |
| MKC-TC-S0-5-009 | Negative | Contract | P1 | 不允许出现缺少 `success` 字段的响应定义 | 文件存在 | 扫描所有 response schema | 所有 2xx/4xx/5xx 响应均包含 `success` | PRD AC-2 |
| MKC-TC-S0-5-010 | Boundary | Contract | P2 | `data` 在成功与错误响应中类型一致 | 文件存在 | 检查所有 response schema | 成功时 `data` 为对应 payload；错误时 `data` 为 nullable | PRD AC-2 |

### 3.3 接口覆盖

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-011 | Functional | Contract | P0 | 注册接口 `POST /api/v1/auth/register` 存在 | 文件存在 | 搜索 paths | 存在该端点，请求体含 email、password | PRD 接口清单 |
| MKC-TC-S0-5-012 | Functional | Contract | P0 | 登录接口 `POST /api/v1/auth/login` 存在 | 文件存在 | 搜索 paths | 存在该端点 | PRD 接口清单 |
| MKC-TC-S0-5-013 | Functional | Contract | P0 | 刷新 Token 接口 `POST /api/v1/auth/refresh` 存在 | 文件存在 | 搜索 paths | 存在该端点 | PRD 接口清单 |
| MKC-TC-S0-5-014 | Functional | Contract | P0 | 登出接口 `POST /api/v1/auth/logout` 存在 | 文件存在 | 搜索 paths | 存在该端点，security 要求认证 | PRD 接口清单 |
| MKC-TC-S0-5-015 | Functional | Contract | P0 | 文件上传接口 `POST /api/v1/files/upload` 存在 | 文件存在 | 搜索 paths | 存在该端点，content-type 支持 multipart/form-data | PRD 接口清单 |
| MKC-TC-S0-5-016 | Functional | Contract | P0 | 任务列表接口 `GET /api/v1/tasks` 存在 | 文件存在 | 搜索 paths | 存在该端点，支持分页 query | PRD 接口清单 |
| MKC-TC-S0-5-017 | Functional | Contract | P0 | 任务详情接口 `GET /api/v1/tasks/{id}` 存在 | 文件存在 | 搜索 paths | 存在该端点 | PRD 接口清单 |
| MKC-TC-S0-5-018 | Functional | Contract | P0 | 任务进度 SSE 接口 `GET /api/v1/tasks/{id}/progress` 存在 | 文件存在 | 搜索 paths | 存在该端点，响应 mediaType 包含 `text/event-stream` | PRD 接口清单 |
| MKC-TC-S0-5-019 | Negative | Contract | P1 | 未在 Sprint 1 需求中的接口不应出现 | 文件存在 | 人工审查 paths | 无额外业务端点 | PRD AC-4 |

### 3.4 认证与安全设计

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-020 | Security | Contract | P0 | JWT Bearer 认证方案已定义 | 文件存在 | 检查 `components.securitySchemes` | 存在 `bearerAuth` 类型 `http` scheme `bearer` bearerFormat `JWT` | PRD AC-5 |
| MKC-TC-S0-5-021 | Security | Contract | P1 | 受保护端点声明 `security` | 文件存在 | 检查 `/api/v1/auth/logout` 等 | 包含 `security: [bearerAuth: []]` | PRD 接口清单 |
| MKC-TC-S0-5-022 | Security | Contract | P0 | access_token TTL 为 15 分钟 | 文件存在 / 设计文档 | 检查 login/refresh 响应 schema | `expires_in` 为 900 | PRD 认证方式 |
| MKC-TC-S0-5-023 | Security | Contract | P1 | refresh_token 设计说明完整 | 设计文档存在 | 阅读 `docs/api/api-design.md` | 说明 refresh_token 为随机字符串、存储于 Redis、有效期 7 天、可吊销 | PRD 认证方式 |
| MKC-TC-S0-5-024 | Security | Contract | P2 | 上传接口文件大小限制在设计中声明 | 文件存在 | 检查 `/api/v1/files/upload` 参数或描述 | 说明最大文件大小与支持的类型 | PRD AC-4 |
| MKC-TC-S0-5-025 | Security | Static | P1 | 接口路径与字段名无敏感信息泄露 | 文件存在 | 搜索 `password`、`secret`、`token` 在路径中 | 不存在 `/password` 等敏感路径 | 安全基线 |

### 3.5 错误码

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-026 | Functional | Contract | P0 | 错误码表在文档中定义 | 文件存在 | 检查 `docs/api/api-design.md` 或 openapi 的 description | 包含 `BAD_REQUEST`、`UNAUTHORIZED`、`FORBIDDEN`、`NOT_FOUND`、`CONFLICT`、`INTERNAL_ERROR` 等 | PRD AC-4 |
| MKC-TC-S0-5-027 | Functional | Contract | P1 | 业务错误码与 HTTP 状态码对照正确 | 文件存在 | 抽样检查响应 | `AUTH_INVALID_CREDENTIALS` 对应 401，`FILE_TOO_LARGE` 对应 413 | PRD 错误码规范 |
| MKC-TC-S0-5-028 | Boundary | Contract | P2 | 错误 message 为中文或可读文本 | 文件存在 | 检查示例 | message 为 `"邮箱或密码错误"` 等用户友好文本 | PRD 错误响应 |
| MKC-TC-S0-5-029 | Negative | Contract | P1 | 不允许未定义的错误码 | 文件存在 | 搜索所有 `error.code` 枚举 | 所有错误码均来自错误码表 | PRD AC-4 |

### 3.6 命名规范

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-030 | Functional | Static | P0 | URL 路径使用 kebab-case | 文件存在 | 扫描所有 path | 全小写、单词间用 `-` 连接 | PRD 技术要点 |
| MKC-TC-S0-5-031 | Functional | Static | P0 | 字段名使用 snake_case | 文件存在 | 抽样检查 schema 字段 | 字段名为 `user_id`、`resource_id`、`created_at` 等 | PRD 技术要点 |
| MKC-TC-S0-5-032 | Negative | Static | P1 | URL 路径不含大写或下划线 | 文件存在 | 正则扫描 paths | 无 `/api/v1/UserProfile` 或 `/api/v1/user_profile` | PRD 技术要点 |
| MKC-TC-S0-5-033 | Negative | Static | P1 | 字段名不含大写或 kebab-case | 文件存在 | 正则扫描 request/response 字段 | 无 `userId`、`user-ID` 等 | PRD 技术要点 |

### 3.7 Swagger UI

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-034 | Functional | E2E | P1 | Gateway 启动后 `/swagger/index.html` 可访问 | Gateway 已部署 | 浏览器访问 `http://mkc.local/swagger/index.html` | 显示 Swagger UI 并加载 openapi.json | PRD AC-6 |
| MKC-TC-S0-5-035 | Functional | E2E | P2 | Swagger UI 展示的接口与手写 OpenAPI 一致 | Gateway 已部署 | 对比 `/swagger/doc.json` 与 `docs/api/openapi.yaml` | 路径、方法、参数一致 | PRD AC-6 |
| MKC-TC-S0-5-036 | Functional | Static | P1 | README 说明 Swagger UI 访问方式 | 仓库已克隆 | `grep -i swagger README.md` | 存在访问链接或说明 | PRD AC-7 |

### 3.8 契约/兼容性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-037 | Contract | Contract | P1 | 生成客户端 SDK 无错误 | openapi.yaml 有效 | `openapi-generator-cli generate -i docs/api/openapi.yaml -g dart` | 生成成功，无 fatal error | PRD 技术要点 |
| MKC-TC-S0-5-038 | Contract | Contract | P1 | 生成服务端 stub 无错误 | openapi.yaml 有效 | `openapi-generator-cli generate -i docs/api/openapi.yaml -g go-server` | 生成成功 | PRD 技术要点 |
| MKC-TC-S0-5-039 | Compatibility | Contract | P2 | 新增接口不破坏已有 schema | 后续 Sprint 更新 | 使用 openapi diff 工具 | 无破坏性变更（breaking changes） | PRD 阻塞风险 |
| MKC-TC-S0-5-040 | Idempotency | Contract | P2 | 同一份 openapi.yaml 多次校验结果一致 | 文件存在 | 连续运行 validate 3 次 | 结果一致 | 工程最佳实践 |

### 3.9 异常与边界

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-5-041 | Exception | Contract | P1 | 缺失必填字段时 schema 有 `required` 声明 | 文件存在 | 检查 register/login/upload 请求体 | `required` 包含 email、password、file 等 | PRD 接口示例 |
| MKC-TC-S0-5-042 | Boundary | Contract | P2 | email 字段有格式约束 | 文件存在 | 检查 schema | `email` 字段 format 为 `email` | PRD 接口示例 |
| MKC-TC-S0-5-043 | Boundary | Contract | P2 | 分页参数有合理默认值/最大值 | 文件存在 | 检查 tasks 列表 query 参数 | `page` 默认 1，`limit` 默认 20 且有最大值限制 | PRD 分页响应 |
| MKC-TC-S0-5-044 | Security | Contract | P2 | SSE 接口不会返回敏感错误细节 | 文件存在 | 检查 SSE 错误事件格式 | 错误仅暴露 code/message，无堆栈或内部状态 | 安全基线 |

## 4. 测试执行清单

- [ ] `docs/api/openapi.yaml` 存在并通过校验
- [ ] 所有 Sprint 1 必需接口已定义
- [ ] 统一响应信封、错误码、认证方案符合规范
- [ ] URL 与字段命名规范通过检查
- [ ] Swagger UI 可访问（Gateway 部署后）
- [ ] 可生成 Dart/Go SDK 且无致命错误

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
