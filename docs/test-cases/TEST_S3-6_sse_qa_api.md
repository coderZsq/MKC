# S3-6 测试用例：实现 SSE 问答 API

## 1. 范围与目标

验证 Gateway 与 AI Service 的 SSE 问答链路：Gateway 端点、AI Service 问答编排、检索 + LLM 流式生成、SSE 事件转发、消息持久化、错误处理与 Web 端兼容。

## 2. 测试环境

- Gateway：Go 1.22+，Gin 1.10+
- AI Service：Python 3.11+，Flask/FastAPI
- Redis（会话状态可选）
- MySQL（消息持久化）
- 浏览器/ChromeDriver（Web 集成测试）

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-6-001 | Functional | Integration | P0 | Gateway 建立 SSE 问答连接 | 已登录，有会话 | POST /api/v1/conversations/{id}/ask | 返回 SSE 流 | PRD AC-1 |
| MKC-TC-S3-6-002 | Functional | Integration | P0 | 问答流式返回答案 | 已上传文件并索引 | 提问并消费 SSE | 收到 chunk 事件与完整答案 | PRD AC-4 |
| MKC-TC-S3-6-003 | Functional | Integration | P1 | AI Service 完成检索与生成 | 已索引数据 | POST /ai/v1/qa/stream | 返回 chunk/done 事件 | PRD AC-3 |
| MKC-TC-S3-6-004 | Functional | Integration | P1 | 答案包含引用来源 | 已索引数据 | 提问并消费 SSE | 收到 citation 事件 | PRD AC-6 |
| MKC-TC-S3-6-005 | Functional | Integration | P1 | 问答完成后消息被持久化 | 提问完成 | 查询消息表 | 用户问题与助手答案存在 | PRD AC-7 |
| MKC-TC-S3-6-006 | Functional | E2E | P2 | 端到端提问获得流式答案 | 完整环境 | Flutter/Web 提问 | 看到实时流式答案 | PRD AC-4 |
| MKC-TC-S3-6-007 | Functional | Integration | P2 | 历史消息传入 AI Service | 会话有历史 | 提问 | 请求包含历史 messages | PRD AC-3 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-6-008 | Security | Integration | P0 | 无 JWT 拒绝访问 | 请求无 token | POST /api/v1/conversations/{id}/ask | 返回 401 | PRD AC-1 |
| MKC-TC-S3-6-009 | Security | Integration | P0 | Web 端通过 ?token= 访问 | Web 环境 | 使用 EventSource?token=... | SSE 连接成功 | PRD AC-1 |
| MKC-TC-S3-6-010 | Security | Integration | P1 | 越权访问他人会话 | 使用他人 conversation_id | POST /api/v1/conversations/{id}/ask | 返回 403 | PRD AC-1 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-6-011 | Negative | Integration | P0 | LLM 超时返回 error 事件 | 模拟 LLM 超时 | 提问 | 收到 error 事件，部分答案已保存 | PRD AC-8 |
| MKC-TC-S3-6-012 | Negative | Integration | P1 | AI Service 不可用时返回 503 | 停止 AI Service | 提问 | Gateway 返回 503 | PRD 降级策略 |
| MKC-TC-S3-6-013 | Negative | Integration | P1 | 客户端断开后服务正常结束 | 建立 SSE 后断开 | 观察日志 | 无 goroutine 泄漏 | PRD AC-8 |
| MKC-TC-S3-6-014 | Negative | Integration | P1 | 检索无结果仍生成答案 | 无相关数据 | 提问 | 收到 done 事件，答案提示无上下文 | PRD 降级策略 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-6-015 | Functional | Static | P1 | Go 测试覆盖率 80%+ | 代码存在 | 运行 go test -cover | coverage >= 80% | PRD AC-9 |
| MKC-TC-S3-6-016 | Functional | Static | P1 | Python 测试覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-9 |
| MKC-TC-S3-6-017 | Security | Static | P1 | 无硬编码 AI Service Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-6-018 | Compatibility | E2E | P1 | Web 端 Chrome 流式显示答案 | Chrome 环境 | 提问 | 页面实时显示答案 | PRD AC-1 |
| MKC-TC-S3-6-019 | Compatibility | Widget | P1 | Web 端引用卡片点击跳转 | Chrome 环境 | 点击引用 | 跳转至资源详情 | PRD AC-6 |
| MKC-TC-S3-6-020 | Reliability | E2E | P2 | 断线后重连继续获取 | 流式中刷新页面 | 重新建立 SSE | 可从最新状态继续 | PRD AC-8 |

## 4. 测试执行清单

- [ ] Gateway SSE 问答端点
- [ ] AI Service 检索 + 生成编排
- [ ] 流式答案与引用事件
- [ ] 消息持久化
- [ ] 认证与越权
- [ ] 错误事件与超时
- [ ] Web 端 SSE 兼容
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
