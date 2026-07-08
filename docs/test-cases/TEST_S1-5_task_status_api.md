# S1-5 测试用例：任务创建与状态查询 API

## 1. 范围与目标

验证 Gateway 任务管理 API 在任务创建、列表分页、详情查询、状态机转换与权限隔离上符合 PRD/TECH 要求。

## 2. 测试环境

- Go 1.22+
- MySQL 8 容器
- 已登录用户 access_token
- 已上传资源与任务数据

## 3. 测试用例

### 3.1 列出任务

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-5-001 | Functional | Integration | P0 | 正常列出当前用户任务 | 用户 A 有 3 条任务 | `GET /tasks` | 返回 3 条，状态 200，meta.total=3 | PRD AC-1 |
| MKC-TC-S1-5-002 | Functional | Integration | P0 | 分页参数生效 | 用户 A 有 25 条任务 | `GET /tasks?page=2&limit=10` | 返回第 11-20 条，meta.page=2, limit=10 | PRD AC-1 |
| MKC-TC-S1-5-003 | Security | Integration | P0 | 不返回其他用户任务 | 用户 A/B 各有任务 | A 调用 `GET /tasks` | 结果中无 B 的任务 | PRD 权限 |
| MKC-TC-S1-5-004 | Negative | Integration | P1 | page=0 返回 400 | 已登录 | `GET /tasks?page=0` | 返回 400，code=`VALIDATION_ERROR` | TECH 7 |
| MKC-TC-S1-5-005 | Negative | Integration | P1 | limit>100 返回 400 | 已登录 | `GET /tasks?limit=200` | 返回 400 | TECH 7 |
| MKC-TC-S1-5-006 | Security | Integration | P0 | 未认证返回 401 | 服务运行 | 不带 token | 返回 401 | PRD AC-7 |

### 3.2 查询任务详情

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-5-007 | Functional | Integration | P0 | 查询自己的任务详情 | 任务存在 | `GET /tasks/{task_id}` | 返回完整字段，状态 200 | PRD AC-2 |
| MKC-TC-S1-5-008 | Security | Integration | P0 | 查询他人任务返回 404 | 任务属于用户 B | A 查询 | 返回 404，code=`NOT_FOUND` | PRD 权限 |
| MKC-TC-S1-5-009 | Negative | Integration | P0 | 不存在的 task_id 返回 404 | 服务运行 | `GET /tasks/{random_uuid}` | 返回 404 | PRD AC-2 |
| MKC-TC-S1-5-010 | Security | Integration | P0 | 未认证返回 401 | 服务运行 | 不带 token | 返回 401 | PRD AC-7 |

### 3.3 创建任务

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-5-011 | Functional | Integration | P0 | 为已有资源创建任务 | A 拥有资源 R | `POST /tasks` 传 resource_id | 返回 200，task.status=pending | PRD AC-3 |
| MKC-TC-S1-5-012 | Functional | Integration | P1 | 创建任务时 type 默认使用资源 type | A 拥有资源 R（type=media_parse） | `POST /tasks` 不传 type | task.type=media_parse | TECH 6.1 |
| MKC-TC-S1-5-013 | Negative | Integration | P0 | 为他人资源创建任务返回 404 | 资源属于 B | A 调用 `POST /tasks` | 返回 404 | PRD 权限 |
| MKC-TC-S1-5-014 | Negative | Integration | P0 | resource_id 不存在返回 404 | 已登录 | 传不存在的 resource_id | 返回 404 | TECH 7 |
| MKC-TC-S1-5-015 | Negative | Integration | P1 | 缺少 resource_id 返回 400 | 已登录 | 请求体为空 | 返回 400 | TECH 7 |

### 3.4 状态机

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-5-016 | Functional | Unit | P0 | pending 可转为 running | 任务 pending | MarkRunning | 状态变为 running，started_at 写入 | PRD AC-4 |
| MKC-TC-S1-5-017 | Functional | Unit | P0 | running 可转为 completed | 任务 running | MarkCompleted | 状态变为 completed，completed_at 写入 | PRD AC-4 |
| MKC-TC-S1-5-018 | Functional | Unit | P0 | running 可转为 failed | 任务 running | MarkFailed | 状态变为 failed，error_message 写入 | PRD AC-4 |
| MKC-TC-S1-5-019 | Negative | Unit | P0 | pending 不能直接 completed | 任务 pending | MarkCompleted | 返回 `INVALID_STATE_TRANSITION` | PRD AC-4 |
| MKC-TC-S1-5-020 | Negative | Unit | P0 | completed 不能转回 running | 任务 completed | MarkRunning | 返回非法状态转换 | PRD AC-4 |
| MKC-TC-S1-5-021 | Functional | Unit | P1 | 更新 progress 0-100 | 任务 running | UpdateProgress(50) | progress=50 | PRD AC-5 |
| MKC-TC-S1-5-022 | Negative | Unit | P1 | progress 超过 100 返回 400 | 任务 running | UpdateProgress(101) | 返回 400 | TECH 7 |
| MKC-TC-S1-5-023 | Negative | Unit | P1 | 非 running 状态更新 progress 返回 400 | 任务 pending | UpdateProgress(10) | 返回 400 | TECH 6.2 |

### 3.5 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-5-024 | Functional | Static | P1 | 无硬编码密钥 | 代码存在 | 搜索 `secret`、`password` | 无真实密钥 | 安全基线 |
| MKC-TC-S1-5-025 | Functional | Integration | P1 | 测试覆盖率 80%+ | 测试存在 | `go test -cover ./internal/service/... ./internal/handler/...` | 覆盖率 ≥80% | PRD AC-8 |
| MKC-TC-S1-5-026 | Functional | Integration | P1 | race detector 通过 | 测试存在 | `go test -race ./...` | 无 data race | Go Testing 规范 |
| MKC-TC-S1-5-027 | Security | Integration | P1 | 统一 404 不泄露任务存在性 | 任务属于 B | A 查询 | 返回 404 与不存在时一致 | PRD 权限 |

## 4. 测试执行清单

- [ ] 列出任务与分页
- [ ] 任务详情查询与权限隔离
- [ ] 为资源创建任务
- [ ] 状态机合法与非法转换
- [ ] 进度更新边界
- [ ] 未认证返回 401
- [ ] `go test ./...` 通过且覆盖率 80%+
- [ ] `go test -race ./...` 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
