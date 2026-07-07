# API 设计说明

本目录存放 MKC 项目的 API 接口契约。

- `openapi.yaml` — OpenAPI 3.0.3 规范，前后端联调的唯一真理源。
- `api-design.md` — 本文档，说明设计约定与使用方式。

## 基础约定

| 项 | 约定 |
|---|---|
| 协议 | HTTP/1.1、HTTP/2（部署后） |
| 数据格式 | JSON，统一使用 UTF-8 |
| URL 版本 | `/api/v1/` |
| URL 风格 | kebab-case，全小写 |
| 字段风格 | snake_case |
| 认证 | JWT access_token + Redis Session refresh_token |

## 统一响应信封

所有接口返回相同的顶层结构：

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { ... }
}
```

- `success`：布尔值，请求是否成功。
- `data`：成功时返回业务数据；失败时为 `null`。
- `error`：失败时返回 `{ code, message, details? }`；成功时为 `null`。
- `meta`：可选元数据，包含 `request_id`、`timestamp`；分页响应额外包含 `page`、`limit`、`total`。

## 认证方式

### access_token

- 短期 JWT，有效期 **15 分钟**（`expires_in = 900`）。
- 请求头：`Authorization: Bearer <access_token>`。
- Gateway 无状态校验 JWT 签名。

### refresh_token

- 随机字符串，有效期 **7 天**。
- 存储于 Redis：`refresh:{user_uuid}:{token_uuid}`。
- 用于换取新的 access_token；登出时从 Redis 删除以吊销。

## Sprint 1 接口清单

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 用户注册 | 否 |
| POST | `/api/v1/auth/login` | 用户登录 | 否 |
| POST | `/api/v1/auth/refresh` | 刷新 access_token | 否（需 refresh_token） |
| POST | `/api/v1/auth/logout` | 用户登出 | 是 |
| POST | `/api/v1/files/upload` | 文件上传（预留分片字段） | 是 |
| GET | `/api/v1/tasks` | 任务列表 | 是 |
| GET | `/api/v1/tasks/{task_id}` | 任务详情 | 是 |
| GET | `/api/v1/tasks/{task_id}/progress` | 任务进度 SSE | 是 |

## 错误码

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

## SSE 流式接口

任务进度与后续 AI 流式问答使用 `text/event-stream`：

```text
id: 1
event: chunk
data: {"progress": 30}

id: 2
event: done
data: {"progress": 100, "done": true}
```

错误事件仅暴露 `code` 与 `message`，不携带堆栈或内部状态。

## 验证

使用 `openapi_spec_validator` 校验：

```bash
python -m openapi_spec_validator docs/api/openapi.yaml
```

或使用 Docker：

```bash
docker run --rm -v $(pwd)/docs/api:/spec \
  openapitools/openapi-generator-cli validate -i /spec/openapi.yaml
```

## Swagger UI

Gateway 启动后，Swagger UI 默认挂载在：

```text
http://mkc.local/swagger/index.html
```

在本地开发环境可通过相同路径访问。

## 版本升级规则

- 向后兼容的改动保留在 v1。
- 破坏性改动引入 v2，v1 保留至少 6 个月。
- 废弃接口通过响应头 `Deprecation` 提醒。
