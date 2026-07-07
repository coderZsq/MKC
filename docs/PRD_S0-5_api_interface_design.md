# PRD：[S0-5] 设计 API 接口文档

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](./AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-5 |
| **任务名称** | 设计 API 接口文档 |
| **所属史诗** | E0 基础设施 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S0-4 数据库 Schema |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要在 Sprint 0 完成 API 接口的初稿设计，定义统一的路由前缀、请求/响应格式、错误码规范和核心端点。该文档将作为前后端联调的契约，并在后续 Sprint 中按需迭代。

---

## 验收标准（AC）

- [ ] 编写 OpenAPI 3.0 / Swagger 2.0 规范文档，位于 `docs/api/openapi.yaml`
- [ ] 定义统一响应信封：`{ "success": bool, "data": any, "error": object|null, "meta": object|null }`
- [ ] 覆盖 Sprint 1 必需的接口：注册、登录、刷新 Token、登出、文件上传、任务查询
- [ ] 定义 HTTP 状态码与业务错误码对照表
- [ ] 定义认证方式：JWT access_token + Redis Session refresh_token
- [ ] Gateway 集成 Swagger UI，开发阶段可在线查看文档
- [ ] README 中说明如何访问 Swagger UI

---

## 统一响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": null
}
```

### 分页成功响应

```json
{
  "success": true,
  "data": [ ... ],
  "error": null,
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### 错误响应

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "邮箱或密码错误"
  },
  "meta": null
}
```

---

## 接口清单（Sprint 1 使用）

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | /api/v1/auth/register | 用户注册 | 否 |
| POST | /api/v1/auth/login | 用户登录 | 否 |
| POST | /api/v1/auth/refresh | 刷新 access_token | 否（需 refresh_token） |
| POST | /api/v1/auth/logout | 用户登出 | 是 |
| POST | /api/v1/files/upload | 文件上传（支持分片） | 是 |
| GET | /api/v1/tasks | 任务列表 | 是 |
| GET | /api/v1/tasks/:id | 任务详情 | 是 |
| GET | /api/v1/tasks/:id/progress | 任务进度 SSE | 是 |

---

## 关键接口示例

### POST /api/v1/auth/login

**请求体：**
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**响应体：**
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "access_token": "eyJhbG...",
    "refresh_token": "random_session_token",
    "expires_in": 900,
    "token_type": "Bearer"
  }
}
```

### POST /api/v1/files/upload

**请求：**
- Content-Type: multipart/form-data
- 字段：`file`（二进制文件）

**响应体：**
```json
{
  "success": true,
  "data": {
    "resource_id": "uuid",
    "name": "meeting.mp3",
    "type": "mp3",
    "status": "uploading",
    "size_bytes": 1234567
  }
}
```

---

## 认证方式

- **access_token**：短期 JWT，有效期 15 分钟
  - 请求头：`Authorization: Bearer <access_token>`
  - Gateway 无状态校验 JWT 签名
- **refresh_token**：随机字符串，有效期 7 天，存储于 Redis Session
  - 用于换取新的 access_token
  - 支持登出吊销和多设备会话管理

---

## 错误码规范

| 错误码 | HTTP 状态 | 说明 |
|---|---|---|
| BAD_REQUEST | 400 | 请求参数错误 |
| UNAUTHORIZED | 401 | access_token 缺失或失效 |
| FORBIDDEN | 403 | 无权限 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突，如邮箱已注册 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| AUTH_INVALID_CREDENTIALS | 401 | 登录凭据错误 |
| AUTH_SESSION_EXPIRED | 401 | refresh_token 已过期或被吊销 |
| FILE_TOO_LARGE | 413 | 文件超过大小限制 |
| FILE_UNSUPPORTED_TYPE | 415 | 不支持的文件类型 |

---

## 文件位置

```
docs/
├── api/
│   ├── openapi.yaml          # OpenAPI 规范
│   └── api-design.md         # 设计说明与约定
└── README.md
```

---

## 技术要点

- 使用 **OpenAPI 3.0** 规范，可被 Swagger UI、Postman、Insomnia 直接导入
- Gateway 使用 `gin-swagger` 在 `/swagger/index.html` 暴露文档
- 接口版本统一为 `/api/v1/`
- 所有路径使用 kebab-case，字段名使用 snake_case
- 上传接口后续需支持分片上传，Schema 设计时预留 `upload_id`、`chunk_index` 字段

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 后续 Sprint 接口扩展导致文档滞后 | 前后端契约不一致 | 每个 Sprint 开始前先更新接口文档 |
| Swagger UI 依赖注释生成 | 与手写 OpenAPI 重复 | 以手写 OpenAPI 为准，Swagger UI 仅做展示 |

---

## 备注

- 本任务只输出接口文档，不实现具体 handler
- 文档应随 Sprint 推进持续更新，建议在 PR 中强制 review
- 后续会补充 RAG 问答、Agent 会话、评估等接口
