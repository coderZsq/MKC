# PRD：[S1-3] 实现文件上传 API

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 关联文档：[PRD_S1-1_user_auth_api.md](./PRD_S1-1_user_auth_api.md)、[TECH_S1-3_file_upload_api.md](../tech/TECH_S1-3_file_upload_api.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S1-3 |
| **任务名称** | 实现文件上传 API |
| **所属史诗** | E2 资源管理 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S1-1 用户认证 API、S0-4 数据库 Schema、S0-7 Go Gateway 骨架 |
| **目标 Sprint** | Sprint 1 |

---

## 描述

作为用户，我需要上传多媒体文件（音频、视频、PDF、文档）到系统，并自动触发异步解析任务。本任务在 Gateway 实现 `POST /api/v1/files/upload`，接收 multipart/form-data，完成文件校验、对象存储落盘、资源元数据落库，并创建后续 AI 解析任务。

---

## 验收标准（AC）

- [ ] **AC-1** `POST /api/v1/files/upload` 仅允许已登录用户访问
- [ ] **AC-2** 支持 `multipart/form-data` 单文件上传
- [ ] **AC-3** 最大文件大小 500 MB，超出返回 `413`
- [ ] **AC-4** 校验文件 MIME 类型白名单，不支持的类型返回 `415`
- [ ] **AC-5** 上传成功后文件写入 MinIO，生成 `storage_key`
- [ ] **AC-6** 在 `resources` 表创建记录，状态为 `uploading`（1）
- [ ] **AC-7** 在 `tasks` 表创建解析任务，状态为 `pending`
- [ ] **AC-8** 响应返回 resource_id、name、type、status、size_bytes
- [ ] **AC-9** 预留 `upload_id` / `chunk_index` 字段，当前 Sprint 不实现分片上传但保留扩展性
- [ ] **AC-10** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
gateway/
├── internal/
│   ├── handler/
│   │   └── file_handler.go
│   ├── service/
│   │   └── file_service.go
│   ├── repository/
│   │   ├── resource_repository.go
│   │   └── task_repository.go
│   ├── model/
│   │   ├── resource.go            # 已存在，复用
│   │   └── task.go                # 已存在，复用
│   └── storage/
│       └── minio_client.go        # MinIO 封装
├── internal/config/config.go      # 增加 minio 配置段
└── pkg/response/response.go       # 已存在，复用
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| minio/minio-go/v7 | v7.x | MinIO / S3 对象存储 |
| gin-gonic/gin | v1.10.x | multipart 解析 |
| google/uuid | v1.x | resource/task UUID |
| gorm.io/gorm | v1.25.x | 资源/任务落库 |

---

## 技术要点

### 文件校验

- 先解析 multipart header，避免一次性读入大文件到内存
- 校验扩展名与 MIME 类型白名单；两者不一致时以 MIME 为准
- 单文件大小限制 500 MB，通过 Gin 的 `MaxMultipartMemory` 与自定义 `Content-Length` 校验共同控制

### MinIO 存储

- bucket：`mkc-resources`
- key 格式：`{user_uuid}/{resource_uuid}/{safe_filename}`
- 使用 MinIO `PutObject` 流式上传，避免内存拷贝
- 上传成功后 `resources.storage_key` 写入完整 key

### 任务创建

- 文件落盘成功后，创建 Task：
  - `type`: `media_parse`（预留 `pdf_parse`、`audio_transcribe` 等）
  - `status`: `pending`
  - `progress`: 0
  - `resource_id`: 新 resource 的 id
- Task 创建与 MinIO 上传失败时整体回滚：删除已上传对象、标记资源状态为失败

### 错误处理

- `413`：`FILE_TOO_LARGE`
- `415`：`FILE_UNSUPPORTED_TYPE`
- 上传过程中 MinIO/DB 失败：`INTERNAL_ERROR`
- 所有错误不暴露 MinIO 内部地址或 bucket 信息

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| MinIO 未部署 | 上传无法落盘 | 本地开发使用 Docker Compose MinIO；CI 使用 `minio/minio` 测试容器 |
| 大文件导致网关内存暴涨 | OOM | 使用流式上传；设置 `MaxMultipartMemory` 为 32 MB |
| MIME 类型伪造 | 安全风险 | 使用 `http.DetectContentType` 读取前 512 字节校验 magic bytes |

---

## Web 端适配

- Web 端 Flutter 上传使用 `MultipartFile.fromBytes`，Gateway 对 `multipart/form-data` 的解析与校验逻辑与移动端一致。
- Gateway 需配置 CORS：允许 Flutter Web 启动域名、允许 `POST /api/v1/files/upload` 的 `multipart/form-data` Content-Type、允许携带 `Authorization` 头或 credentials。
- Web 端上传同样受 500MB 服务端大小限制，但前端建议限制 ≤100MB 以避免浏览器内存占用过高。
- Web 端集成测试使用 ChromeDriver；单元/接口测试使用 `flutter test --platform chrome` 与 Go 测试容器。

---

## 备注

- 当前 Sprint 只支持单文件整体上传，分片字段仅为预留
- 上传成功后不阻塞等待 AI 解析完成，立即返回 resource/task 信息
- 文件类型与后续任务类型的映射：
  - `audio/*`, `video/*` → `media_parse`
  - `application/pdf` → `pdf_parse`
  - 其他文档 → `document_parse`
- 上传同名文件视为新资源，不覆盖旧资源
