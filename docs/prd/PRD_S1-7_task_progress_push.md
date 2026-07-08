# PRD：[S1-7] 实现 SSE/WebSocket 任务进度实时推送

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 关联文档：[PRD_S1-5_task_status_api.md](./PRD_S1-5_task_status_api.md)、[PRD_S1-6_flutter_task_center.md](./PRD_S1-6_flutter_task_center.md)、[TECH_S1-7_task_progress_push.md](../tech/TECH_S1-7_task_progress_push.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S1-7 |
| **任务名称** | 实现 SSE/WebSocket 任务进度实时推送 |
| **所属史诗** | E3 任务管理 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S1-5 任务 API、S1-6 任务中心页面 |
| **目标 Sprint** | Sprint 1 |

---

## 描述

作为用户，当我从 iOS、Android 或 Web（Chrome）端进入任务中心并查看运行中的任务时，我希望任务进度能够实时更新，而无需手动刷新页面。本任务在 Gateway 与 Flutter 客户端之间建立基于 Server-Sent Events（SSE）的实时进度推送通道，并提供失败时的降级轮询机制。

---

## 验收标准（AC）

- [ ] **AC-1** Gateway 提供 `GET /api/v1/tasks/{task_id}/events` SSE 端点
- [ ] **AC-2** SSE 端点需 JWT 认证，客户端可通过 `Authorization` 头或 `token` 查询参数传 token
- [ ] **AC-3** SSE 事件类型：`progress`（进度更新）、`status`（状态变更）、`done`（完成）、`error`（失败）
- [ ] **AC-4** 事件 payload 包含 `progress`、`status`、`message`、`timestamp`
- [ ] **AC-5** 当任务状态推进或进度变化时，订阅该任务的所有客户端立即收到事件
- [ ] **AC-6** 客户端断开连接时，服务器清理订阅资源，避免 goroutine 泄漏
- [ ] **AC-7** Flutter 任务中心在查看运行中任务时自动订阅 SSE，实时刷新进度与状态
- [ ] **AC-8** Web（Chrome）端使用浏览器 `EventSource` 或兼容库订阅 SSE，通过 `?token=` 传递 JWT，收到事件后更新任务状态
- [ ] **AC-9** 当 SSE 连接失败时，客户端自动降级为每 5 秒轮询任务详情
- [ ] **AC-10** 单元/集成测试覆盖率 80%+（含 Web SSE 轮询/降级验证）

---

## 推荐目录结构

### Gateway

```
gateway/
├── internal/
│   ├── handler/
│   │   └── task_sse_handler.go
│   ├── service/
│   │   └── task_broadcaster.go
│   └── router/
│       └── router.go              # 注册 SSE 路由
└── pkg/sse/
    └── sse.go                     # 通用 SSE writer
```

### Flutter

```
client/lib/
├── data/
│   └── datasources/remote/
│       └── task_sse_client.dart
├── presentation/
│   ├── pages/
│   │   └── task_center_page.dart
│   └── providers/
│       └── task_center_provider.dart
└── shared/
    └── utils/
        └── sse_parser.dart
```

---

## 核心依赖

### Gateway

| 依赖 | 版本 | 用途 |
|---|---|---|
| gin-gonic/gin | v1.10.x | HTTP 路由与流式响应 |
| 标准库 `context`、`sync` | - | 订阅管理与清理 |

### Flutter

| 依赖 | 版本 | 用途 |
|---|---|---|
| dio | 5.4.x | SSE 流式读取 |
| flutter_riverpod | 2.5.x | 订阅生命周期管理 |

---

## 技术要点

### SSE 事件格式

```text
event: progress
data: {"task_id":"...","progress":35,"status":"running","timestamp":"..."}

```

```text
event: done
data: {"task_id":"...","progress":100,"status":"completed","timestamp":"..."}

```

```text
event: error
data: {"task_id":"...","status":"failed","message":"...","timestamp":"..."}

```

### 认证方式

- 首选：请求头 `Authorization: Bearer <access_token>`
- 兼容：查询参数 `?token=<access_token>`
- 统一由 Gateway auth 中间件解析并校验用户是否有权访问该任务

### 订阅管理

- 每个 task 维护一个订阅者列表
- 使用 `sync.RWMutex` 保证并发安全
- 客户端断开时立即从列表移除并关闭 channel
- 任务完成/失败后保留事件 30 秒再清理订阅列表

### 客户端行为

- 仅在任务状态为 `running` 时订阅 SSE
- SSE 连接断开后自动重连，最多重试 5 次
- 重试失败后切换为 5 秒轮询，直到任务结束
- 页面离开（dispose）时取消订阅

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 大量运行中任务同时推送 | 内存/连接压力 | 单任务单 goroutine 广播；限制单任务最大订阅数（如 10） |
| 移动端切后台导致连接断开 | 实时性下降 | 切回前台自动重连并立即拉取最新状态 |
| 企业网络/代理屏蔽 SSE | 推送不可用 | 提供 5 秒轮询降级 |

---

## Web 端适配

- Web 端浏览器 `EventSource` 不支持设置自定义请求头，因此必须通过 `?token=<access_token>` 查询参数传递 JWT；Gateway auth 中间件同时支持 Header 与 Query 参数校验。
- Gateway 需要为 SSE 端点配置 CORS：允许 Flutter Web 启动域名、允许 `text/event-stream` 响应类型、允许携带查询参数。
- Web 端 SSE 客户端优先使用浏览器原生 `EventSource`（dart:html）或 `eventsource` / `fetch_event_source` 兼容包；移动端/桌面端使用 dio 流式读取。
- Web 端 SSE 连接断开后同样执行自动重连与轮询降级，最多重试 5 次。
- Web 端 Widget/单元测试使用 `flutter test --platform chrome`；集成测试使用 ChromeDriver 验证任务进度自动刷新。

---

## 备注

- Sprint 1 先实现 SSE；WebSocket 方案作为后续扩展保留设计空间
- 事件 payload 中的 `message` 仅用于 `error` 事件，其他事件可为 null
- 任务状态从 `running` 变为 `completed`/`failed` 后，发送 `done`/`error` 事件并关闭该任务的所有 SSE 连接
- Flutter 端可通过 `provider.overrideWith` 在测试中注入 mock SSE 流
