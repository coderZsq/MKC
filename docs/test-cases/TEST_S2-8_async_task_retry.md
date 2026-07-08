# S2-8 测试用例：转录/解析任务异步执行与失败重试

## 1. 范围与目标

验证任务异步调度与重试机制：Gateway 任务分派、Celery 执行、自动重试、手动重试、状态同步与错误处理。

## 2. 测试环境

- Go 1.22+ / Python 3.11+
- Redis + Celery Worker
- MySQL/Redis
- JWT 已配置

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-8-001 | Functional | Integration | P0 | MP3 任务自动分派到 ASR Celery | 上传 MP3 并创建任务 | 查看任务状态 | Celery 收到 asr_task | PRD AC-1 |
| MKC-TC-S2-8-002 | Functional | Integration | P0 | PDF 任务自动分派到 PDF 解析 Celery | 上传 PDF 并创建任务 | 查看任务状态 | Celery 收到 pdf_parse_task | PRD AC-1 |
| MKC-TC-S2-8-003 | Functional | Integration | P0 | Celery 执行时上报进度 | 任务 running | 查看任务详情 | progress 变化 | PRD AC-2 |
| MKC-TC-S2-8-004 | Functional | Integration | P1 | 失败后自动重试 | 模拟任务失败 | 等待重试 | attempt_count 增加，状态再次 running | PRD AC-3 |
| MKC-TC-S2-8-005 | Functional | Integration | P0 | 手动重试成功 | 任务 failed | POST retry | 状态重置为 pending/running | PRD AC-5 |
| MKC-TC-S2-8-006 | Functional | Unit | P1 | 手动重试重置 attempt_count | 任务 failed | 调用 retry | attempt_count=0 | PRD AC-6 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-8-007 | Security | Integration | P0 | 用户只能重试自己的任务 | 其他用户任务 | POST retry | 返回 404 | PRD 权限 |
| MKC-TC-S2-8-008 | Security | Integration | P1 | 无 JWT 拒绝重试 | 无 Token | POST retry | 返回 401 | TECH 3 |
| MKC-TC-S2-8-009 | Security | Static | P1 | 无硬编码 Redis/Celery 密码 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-8-010 | Negative | Integration | P0 | 最大重试后标记 failed | 连续失败 | 等待重试 | 状态 failed，错误信息记录 | PRD AC-4 |
| MKC-TC-S2-8-011 | Negative | Integration | P1 | 非失败/完成状态不可重试 | 任务 running | POST retry | 返回 TASK_NOT_RETRYABLE | PRD AC-5 |
| MKC-TC-S2-8-012 | Negative | Integration | P1 | 重试过于频繁返回 429 | 刚刚重试过 | POST retry | 返回 RETRY_TOO_FREQUENT | PRD 阻塞风险 |
| MKC-TC-S2-8-013 | Negative | Integration | P1 | Celery Worker 未启动返回 503 | 停止 Worker | 创建任务 | 返回 WORKER_UNAVAILABLE | 阻塞风险 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-8-014 | Functional | Static | P1 | Go/Python 测试覆盖率 80%+ | 代码存在 | 运行测试 | coverage >= 80% | PRD AC-7 |
| MKC-TC-S2-8-015 | Functional | Static | P1 | 静态检查通过 | 代码存在 | 运行 go vet / ruff | 0 issues | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-8-016 | Compatibility | Widget | P1 | Web 端失败任务显示重试按钮 | 任务 failed | 打开任务中心 | 显示重试按钮 | PRD Web 适配 |
| MKC-TC-S2-8-017 | Compatibility | Integration | P1 | Web 端手动重试刷新任务 | 点击重试 | 等待 | 任务状态更新 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] MP3 任务分派到 ASR
- [ ] PDF 任务分派到 PDF 解析
- [ ] 进度上报
- [ ] 自动重试
- [ ] 手动重试接口
- [ ] 重试权限与冷却
- [ ] 最大重试后失败
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
