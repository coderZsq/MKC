# S2-6 测试用例：存储转录/解析结果到对象存储和数据库

## 1. 范围与目标

验证结果存储链路：MinIO 上传、task.result 更新、Gateway 结果查询 API、签名 URL 与权限控制。

## 2. 测试环境

- Go 1.22+ / Python 3.11+
- MinIO 服务可用
- MySQL/Redis 已启动
- JWT 已配置

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-6-001 | Functional | Integration | P0 | AI Service 上传结果到 MinIO | 任务完成 | 调用 upload_result | MinIO 中存在文件 | PRD AC-1 |
| MKC-TC-S2-6-002 | Functional | Integration | P0 | task.result 更新正确 | 上传完成 | 查询数据库 | result 含文件路径 | PRD AC-4 |
| MKC-TC-S2-6-003 | Functional | Integration | P0 | Gateway 返回结果摘要 | 任务 completed | GET /tasks/{id}/result | 返回 files 与 metadata | PRD AC-5 |
| MKC-TC-S2-6-004 | Functional | Unit | P1 | 签名 URL 有效期 1 小时 | 调用 presign | 检查 URL 参数 | 过期时间约 1 小时 | PRD AC-6 |
| MKC-TC-S2-6-005 | Functional | Integration | P1 | 多文件结果同时返回 | 任务含 transcript 与 subtitle | 查询结果 | 多个 URL 均非空 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-6-006 | Security | Integration | P0 | 用户只能访问自己的任务结果 | 其他用户任务 | GET 结果 | 返回 404 | PRD 权限 |
| MKC-TC-S2-6-007 | Security | Integration | P1 | 无 JWT 拒绝访问 | 无 Token | GET 结果 | 返回 401 | TECH 3 |
| MKC-TC-S2-6-008 | Security | Static | P1 | 无硬编码 MinIO 凭证 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-6-009 | Negative | Integration | P0 | 任务未完成返回 400 | 任务 running | GET 结果 | 返回 TASK_NOT_COMPLETED | PRD AC-5 |
| MKC-TC-S2-6-010 | Negative | Integration | P1 | 任务不存在返回 404 | 不存在 task_id | GET 结果 | 返回 TASK_NOT_FOUND | PRD AC-5 |
| MKC-TC-S2-6-011 | Negative | Integration | P1 | MinIO 上传失败任务失败 | 模拟 MinIO 异常 | 上传结果 | 任务状态 failed | 阻塞风险 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-6-012 | Functional | Static | P1 | Go/Python 测试覆盖率 80%+ | 代码存在 | 运行测试 | coverage >= 80% | PRD AC-7 |
| MKC-TC-S2-6-013 | Functional | Static | P1 | 静态检查通过 | 代码存在 | 运行 go vet / ruff | 0 issues | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-6-014 | Compatibility | Integration | P1 | Web 端可通过签名 URL 下载 | 签名 URL 生成 | 通过浏览器下载 | 文件可下载 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] MinIO 上传结果文件
- [ ] task.result 更新
- [ ] Gateway 结果查询
- [ ] 签名 URL 有效期
- [ ] 权限控制
- [ ] 错误处理
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
