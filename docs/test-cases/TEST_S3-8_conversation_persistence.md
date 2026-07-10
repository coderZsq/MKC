# S3-8 测试用例：会话与消息持久化

## 1. 范围与目标

验证 Gateway 会话与消息持久化模块：数据库 schema、会话 CRUD、消息分页、上下文窗口管理、权限校验、级联删除与测试覆盖率。

## 2. 测试环境

- Go 1.22+
- Gin 1.10+
- GORM 1.25+
- MySQL 8.0+
- testify, gomock
- httptest

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-8-001 | Functional | Integration | P0 | 创建会话成功 | 已登录 | POST /api/v1/conversations | 返回会话 ID | PRD AC-2 |
| MKC-TC-S3-8-002 | Functional | Integration | P0 | 列出当前用户会话 | 用户有多个会话 | GET /api/v1/conversations | 仅返回该用户会话 | PRD AC-2 |
| MKC-TC-S3-8-003 | Functional | Integration | P0 | 分页获取消息历史 | 会话有 25 条消息 | GET /messages?page=1&limit=20 | 返回 20 条与分页元数据 | PRD AC-3 |
| MKC-TC-S3-8-004 | Functional | Integration | P1 | 删除会话级联删除消息 | 会话有消息 | DELETE /api/v1/conversations/{id} | 会话与消息均删除 | PRD AC-7 |
| MKC-TC-S3-8-005 | Functional | Unit | P1 | 上下文窗口按 token 截断 | 历史消息超 4096 tokens | 调用 BuildMessages | 返回不超过预算的消息 | PRD AC-6 |
| MKC-TC-S3-8-006 | Functional | Unit | P1 | 上下文窗口优先保留最新 | 历史消息较多 | 调用 BuildMessages | 保留最近的问答 | PRD AC-6 |
| MKC-TC-S3-8-007 | Functional | Integration | P2 | 会话标题自动生成 | 创建无标题会话 | 提问后查看 | 标题取自首问题前 20 字 | PRD 备注 |
| MKC-TC-S3-8-008 | Functional | Unit | P2 | 消息角色正确保存 | 创建 user/assistant 消息 | 查询数据库 | role 字段正确 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-8-009 | Security | Integration | P0 | 无 JWT 拒绝访问 | 请求无 token | 调用会话 API | 返回 401 | PRD AC-4 |
| MKC-TC-S3-8-010 | Security | Integration | P0 | 越权访问他人会话 | 使用他人会话 ID | GET /api/v1/conversations/{id} | 返回 403 | PRD AC-4 |
| MKC-TC-S3-8-011 | Security | Integration | P1 | 越权访问他人消息 | 使用他人会话 ID | GET /messages | 返回 403 | PRD AC-4 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-8-012 | Negative | Integration | P0 | 访问不存在的会话 | 随机 ID | GET /api/v1/conversations/{id} | 返回 404 | PRD AC-4 |
| MKC-TC-S3-8-013 | Negative | Integration | P1 | 创建会话参数错误 | 缺少 title | POST /api/v1/conversations | 返回 400 | PRD AC-2 |
| MKC-TC-S3-8-014 | Negative | Unit | P1 | 删除会话失败 | 数据库异常 | 调用 Delete | 返回 500 | PRD AC-7 |
| MKC-TC-S3-8-015 | Negative | Integration | P1 | 消息分页参数越界 | page=0 或 limit=0 | GET /messages | 返回 400 | PRD AC-3 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-8-016 | Functional | Static | P1 | go test 覆盖率 80%+ | 代码存在 | 运行 go test -cover | coverage >= 80% | PRD AC-8 |
| MKC-TC-S3-8-017 | Functional | Static | P1 | go vet / staticcheck 通过 | 代码存在 | 运行 go vet / staticcheck | 0 issues | 工程规范 |
| MKC-TC-S3-8-018 | Security | Static | P1 | 无硬编码数据库密码 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-8-019 | Performance | Unit | P2 | 会话列表查询 < 100ms | 100 条会话 | 调用 List | 耗时 < 100ms | 性能基线 |
| MKC-TC-S3-8-020 | Compatibility | Integration | P2 | 消息时间字段时区正确 | 不同时区 | 创建/查询消息 | 时间显示一致 | PRD 备注 |

## 4. 测试执行清单

- [ ] 会话创建、列出、删除
- [ ] 消息分页与角色保存
- [ ] 上下文窗口截断
- [ ] 权限与越权
- [ ] 错误处理
- [ ] 级联删除
- [ ] 测试覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
