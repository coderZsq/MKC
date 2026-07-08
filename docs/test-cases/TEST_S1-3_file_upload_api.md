# S1-3 测试用例：文件上传 API

## 1. 范围与目标

验证 Gateway 文件上传接口在认证、参数校验、文件大小、MIME 类型、MinIO 存储、资源/任务落库及失败回滚等场景下符合 PRD/TECH 要求。

## 2. 测试环境

- Go 1.22+
- MySQL 8 容器
- MinIO 容器（bucket `mkc-resources` 已创建）
- 已登录用户 access_token
- `gateway/` 已编译通过

## 3. 测试用例

### 3.1 认证与权限

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-3-001 | Security | Integration | P0 | 未携带 token 上传返回 401 | 服务运行 | 不带 Authorization 调用 `/files/upload` | 返回 401，code=`UNAUTHORIZED` | PRD AC-1 |
| MKC-TC-S1-3-002 | Security | Integration | P0 | 伪造 token 上传返回 401 | 服务运行 | 携带无效 JWT | 返回 401 | PRD AC-1 |
| MKC-TC-S1-3-003 | Security | Integration | P1 | 用户 A 上传后资源归属用户 A | 用户 A 已登录 | 上传文件 | DB 中 resource.user_id 为 A 的 ID | PRD AC-6 |

### 3.2 文件校验

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-3-004 | Negative | Integration | P0 | 缺少 file 字段返回 400 | 已登录 | multipart 中不包含 file | 返回 400，code=`FILE_MISSING` | TECH 7 |
| MKC-TC-S1-3-005 | Negative | Integration | P0 | 超过 500MB 文件返回 413 | 已登录 | 构造 501MB 文件上传 | 返回 413，code=`FILE_TOO_LARGE` | PRD AC-3 |
| MKC-TC-S1-3-006 | Negative | Integration | P0 | 不支持的 MIME 返回 415 | 已登录 | 上传 `.exe` 或 `image/svg+xml` | 返回 415，code=`FILE_UNSUPPORTED_TYPE` | PRD AC-4 |
| MKC-TC-S1-3-007 | Functional | Unit | P1 | MIME 白名单正确识别音频/视频/PDF | 无 | 传入不同 MIME | 返回预期 task type | TECH 6.1 |
| MKC-TC-S1-3-008 | Security | Integration | P1 | 扩展名伪装但 MIME 不支持仍返回 415 | 已登录 | 文件名为 `.mp3` 但 Content-Type 为 `text/plain` | 按 MIME 判断，返回 415 | TECH 6.1 |

### 3.3 上传成功与落库

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-3-009 | Functional | Integration | P0 | 合法 MP3 上传成功 | 已登录 | 上传 10MB MP3 | 返回 200，含 resource_id、task_id、type=media_parse | PRD AC-5/6/7 |
| MKC-TC-S1-3-010 | Functional | Integration | P0 | 上传后 MinIO 存在对象 | 上传成功 | 通过 MinIO 客户端 list 或 stat | key 为 `{user_uuid}/{resource_uuid}/{filename}` | TECH 6.2 |
| MKC-TC-S1-3-011 | Functional | Integration | P0 | 上传后 resource 记录正确 | 上传成功 | 查询 MySQL | resource.status=1，size_bytes 匹配，storage_key 非空 | PRD AC-6 |
| MKC-TC-S1-3-012 | Functional | Integration | P0 | 上传后 task 记录正确 | 上传成功 | 查询 MySQL | task.status=pending，progress=0，type=media_parse | PRD AC-7 |
| MKC-TC-S1-3-013 | Functional | Integration | P1 | 上传 PDF 创建 pdf_parse 任务 | 已登录 | 上传 PDF | task.type=pdf_parse | PRD 备注 |
| MKC-TC-S1-3-014 | Functional | Integration | P1 | 上传 Word 文档创建 document_parse 任务 | 已登录 | 上传 docx | task.type=document_parse | PRD 备注 |

### 3.4 失败回滚

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-3-015 | Reliability | Integration | P1 | 数据库写入失败删除已上传对象 | 强制 DB 写入失败（如断开连接） | 上传合法文件 | MinIO 中不存在对应 key | TECH 6.2 |
| MKC-TC-S1-3-016 | Reliability | Integration | P1 | 任务创建失败删除已上传对象 | 强制 task 表写入失败 | 上传合法文件 | MinIO 中不存在对应 key；resource 也不存在 | TECH 6.2 |

### 3.5 预留字段

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-3-017 | Functional | Integration | P2 | 上传请求包含 upload_id 不报错 | 已登录 | multipart 带 upload_id | 正常处理并忽略（整文件模式） | PRD AC-9 |
| MKC-TC-S1-3-018 | Functional | Integration | P2 | 上传请求包含 chunk_index 不报错 | 已登录 | multipart 带 chunk_index | 正常处理并忽略 | PRD AC-9 |

### 3.6 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-3-019 | Functional | Static | P1 | 无硬编码 MinIO 密钥 | 代码存在 | 搜索 `minioadmin`、`secret_key` 等 | 仅配置与测试 mock 出现 | 安全基线 |
| MKC-TC-S1-3-020 | Functional | Integration | P1 | 测试覆盖率 80%+ | 测试存在 | `go test -cover ./internal/service/... ./internal/handler/... ./internal/storage/...` | 覆盖率 ≥80% | PRD AC-10 |
| MKC-TC-S1-3-021 | Functional | Integration | P1 | race detector 通过 | 测试存在 | `go test -race ./...` | 无 data race | Go Testing 规范 |
| MKC-TC-S1-3-022 | Performance | Integration | P1 | 500MB 文件上传不 OOM | 测试环境内存受限 | 上传 500MB 文件 | 进程 RSS 增长不超过 100MB | PRD 阻塞风险 |

## 4. 测试执行清单

- [x] 未认证请求返回 401（E2E: `client/integration_test/upload_e2e_test.dart`）
- [x] 缺少 file 字段返回 400（E2E）
- [ ] 超大文件返回 413
- [x] 不支持的 MIME 返回 415（E2E）
- [x] 合法文件上传返回 resource/task（E2E）
- [ ] MinIO 中对象存在且 key 符合规范
- [ ] MySQL resource/task 记录正确
- [ ] 失败时回滚 MinIO 对象
- [ ] MIME 与 task type 映射正确
- [ ] `go test ./...` 通过且覆盖率 80%+
- [ ] `go test -race ./...` 通过
- [ ] 无硬编码密钥

### E2E 自动化覆盖

以下用例已由 `client/integration_test/upload_e2e_test.dart` 覆盖：

- MKC-TC-S1-3-001（实际返回 code=`AUTH_INVALID_TOKEN`，HTTP 401）
- MKC-TC-S1-3-004
- MKC-TC-S1-3-006
- MKC-TC-S1-3-009（MP3 → `type=media_parse`）

运行命令：

```bash
cd client
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/upload_e2e_test.dart -d chrome \
  --dart-define=BASE_URL=http://localhost:8080/api/v1
```

状态：**全部通过**。

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
