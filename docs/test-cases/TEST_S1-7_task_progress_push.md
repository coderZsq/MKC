# S1-7 测试用例：SSE/WebSocket 任务进度实时推送

## 1. 范围与目标

验证 Gateway SSE 任务进度推送端点与 Flutter 客户端订阅、解析、实时刷新、重连降级行为符合 PRD/TECH 要求。

## 2. 测试环境

- Go 1.22+
- Flutter 3.22+
- Android/iOS 模拟器、桌面端或 Chrome（Web）
- S1-5 任务 API 已启动
- Gateway CORS 已配置（Web 集成测试）
- 一个处于 running 状态的任务
- Web 测试：`flutter test --platform chrome`；集成测试需 ChromeDriver

## 3. 测试用例

### 3.1 Gateway SSE 端点

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-7-001 | Functional | Integration | P0 | SSE 连接成功并发送初始状态 | 任务存在且 running | `GET /tasks/{id}/events` | 返回 200，Content-Type=text/event-stream，首条 event=status | PRD AC-1 |
| MKC-TC-S1-7-002 | Functional | Integration | P0 | 进度更新事件正确推送 | 已订阅 SSE | 调用 UpdateProgress(50) | 客户端收到 event=progress，progress=50 | PRD AC-4 |
| MKC-TC-S1-7-003 | Functional | Integration | P0 | 完成事件关闭连接 | 已订阅 SSE | MarkCompleted | 收到 event=done，连接关闭 | PRD AC-4 |
| MKC-TC-S1-7-004 | Functional | Integration | P0 | 失败事件推送错误信息 | 已订阅 SSE | MarkFailed("err") | 收到 event=error，message="err" | PRD AC-4 |
| MKC-TC-S1-7-005 | Functional | Integration | P1 | heartbeat 每 30 秒发送 | 连接保持 | 等待 30s | 收到 `event: heartbeat` | TECH 4.3 |
| MKC-TC-S1-7-006 | Security | Integration | P0 | 未认证返回 401 | 服务运行 | 不带 token | 返回 401 | PRD AC-2 |
| MKC-TC-S1-7-007 | Security | Integration | P0 | 查询参数 token 同样有效 | 服务运行 | `?token=valid_token` | 建立连接 | PRD AC-2 |
| MKC-TC-S1-7-008 | Security | Integration | P0 | 访问他人任务返回 404 | 任务属于 B | A 订阅 | 返回 404 | PRD AC-2 |
| MKC-TC-S1-7-009 | Functional | Unit | P1 | 客户端断开后清理订阅 | 已订阅 | 关闭客户端连接 | broadcaster 中该任务订阅数为 0 | PRD AC-6 |
| MKC-TC-S1-7-010 | Functional | Unit | P1 | 广播器不阻塞发布者 | 订阅者 channel 满 | Publish | 不 panic，可丢弃事件 | TECH 6 |

### 3.2 Flutter 客户端

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-7-011 | Functional | Unit | P0 | SSE 原始流解析为事件 | mock SSE 字节流 | parseSseStream | 产出正确 SseEvent 列表 | TECH 5.1 |
| MKC-TC-S1-7-012 | Functional | Widget | P0 | running 任务自动订阅 SSE | 页面打开，任务 running | 打开 TaskCenterPage | 调用 TaskSseClient.listen | PRD AC-7 |
| MKC-TC-S1-7-013 | Functional | Widget | P0 | 收到 progress 事件更新 UI | mock SSE progress=60 | 发送事件 | 列表项进度变为 60% | PRD AC-7 |
| MKC-TC-S1-7-014 | Functional | Widget | P0 | 收到 done 事件停止订阅 | mock SSE done | 发送事件 | 取消订阅，状态 completed | PRD AC-7 |
| MKC-TC-S1-7-015 | Functional | Widget | P1 | SSE 失败自动轮询 | mock SSE 抛错 | 触发错误 | 启动 5s 定时器拉取任务详情 | PRD AC-8 |
| MKC-TC-S1-7-016 | Functional | Widget | P1 | 页面离开取消订阅 | 页面打开 | 离开页面 | _sseSubscription.cancel 被调用 | PRD AC-6 |
| MKC-TC-S1-7-017 | Functional | Widget | P1 | 非 running 任务不订阅 | 任务 completed | 打开页面 | 不建立 SSE 连接 | PRD 客户端行为 |
| MKC-TC-S1-7-018 | Functional | Integration | P1 | 真实 SSE 进度变化 | API 有 running 任务 | 打开任务中心 | 进度随后端更新自动变化 | PRD AC-7 |

### 3.3 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-7-019 | Functional | Static | P1 | Gateway `go test -race ./...` 通过 | 代码存在 | 运行 race detector | 无 data race | Go 测试规范 |
| MKC-TC-S1-7-020 | Functional | Static | P1 | `flutter analyze` 无错误 | 代码存在 | 运行 `flutter analyze` | 0 issues | 工程规范 |
| MKC-TC-S1-7-021 | Security | Static | P1 | 无内部密钥硬编码 | 代码存在 | 全局搜索 | 无真实密钥 | 安全基线 |
| MKC-TC-S1-7-022 | Functional | Integration | P1 | 测试覆盖率 80%+ | 测试存在 | 运行测试 | Gateway/Flutter 均 ≥80% | PRD AC-10 |

### 3.4 Web 与跨平台兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-7-023 | Compatibility | Unit | P1 | Web 端 SSE 事件解析正确 | mock `EventSource` 事件 | 调用 Web 解析函数 | 产出正确 TaskProgressEvent | TECH 5.5 |
| MKC-TC-S1-7-024 | Security | Integration | P1 | Web 端通过 `?token=` 建立 SSE | 服务运行 | `GET /tasks/{id}/events?token=valid` | 返回 200 并开始推送 | PRD Web AC |
| MKC-TC-S1-7-025 | Compatibility | Widget | P1 | Web 端 running 任务自动订阅 | mock EventSource，任务 running | 打开 TaskCenterPage | 使用 Web 订阅并监听事件 | PRD Web AC |
| MKC-TC-S1-7-026 | Compatibility | Integration | P1 | Web 端进度自动刷新 | ChromeDriver，running 任务 | 打开任务中心 | 进度条随后端更新自动变化 | PRD Web AC |
| MKC-TC-S1-7-027 | Compatibility | Widget | P1 | Web 端 SSE 失败后降级轮询 | mock EventSource 抛错 | 触发错误 | 启动 5s 轮询任务详情 | PRD AC-9 |

## 4. 测试执行清单

- [ ] SSE 连接与初始状态事件
- [ ] progress/status/done/error 事件推送
- [ ] heartbeat 机制
- [ ] 未认证/他人任务返回 401/404
- [ ] 查询参数 token 兼容
- [ ] 客户端断开后订阅清理
- [ ] Flutter SSE 流解析（含 Web 事件映射）
- [ ] running 任务自动订阅与 UI 更新
- [ ] done/error 事件结束订阅
- [ ] SSE 失败降级轮询
- [ ] 页面离开取消订阅
- [ ] Web 端 SSE 连接与进度刷新验证（ChromeDriver）
- [ ] `go test -race ./...` 通过
- [ ] `flutter test` 通过（含 `flutter test --platform chrome` 至少运行一次）
- [ ] `flutter analyze` 0 issues
- [ ] 覆盖率 80%+

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
