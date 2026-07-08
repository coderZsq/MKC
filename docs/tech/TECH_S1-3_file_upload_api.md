# 技术文档：[S1-3] 文件上传 API 设计

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 级别：后端工程师  
> 关联 PRD：[PRD_S1-3_file_upload_api.md](../prd/PRD_S1-3_file_upload_api.md)

---

## 1. 文档目标

定义 Gateway 文件上传模块的接口契约、存储设计、数据流、模块划分与关键代码实现，为 S1-3 编码提供可直接落地的蓝图。

---

## 2. 技术栈

- Go 1.22+
- Gin 1.10.x
- GORM 1.25.x
- MinIO Go SDK v7
- MySQL 8 / Redis 7

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/files/upload` | Bearer JWT | 单文件上传 |

### 3.1 请求/响应示例

**Request**

```http
POST /api/v1/files/upload HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="lecture.mp3"
Content-Type: audio/mpeg

<binary>
------WebKitFormBoundary--
```

**Response 200**

```json
{
  "success": true,
  "data": {
    "resource_id": "01922b9a-...",
    "task_id": "01922b9b-...",
    "name": "lecture.mp3",
    "type": "audio",
    "status": "uploading",
    "size_bytes": 12456789,
    "mime_type": "audio/mpeg",
    "created_at": "2026-07-08T10:00:00Z"
  },
  "error": null,
  "meta": { "request_id": "..." }
}
```

---

## 4. 配置

在 `gateway/internal/config/config.go` 增加：

```go
type MinIOConfig struct {
    Endpoint  string `mapstructure:"endpoint"`
    AccessKey string `mapstructure:"access_key"`
    SecretKey string `mapstructure:"secret_key"`
    Bucket    string `mapstructure:"bucket"`
    UseSSL    bool   `mapstructure:"use_ssl"`
    Region    string `mapstructure:"region"`
}
```

对应 `config.yaml`：

```yaml
minio:
  endpoint: "minio:9000"
  access_key: "${APP_MINIO_ACCESS_KEY}"
  secret_key: "${APP_MINIO_SECRET_KEY}"
  bucket: "mkc-resources"
  use_ssl: false
  region: "us-east-1"
```

---

## 5. 模块设计

### 5.1 Storage 层

```go
package storage

import (
    "context"
    "io"
    "time"
)

// ObjectStorage abstracts file storage (MinIO/S3).
type ObjectStorage interface {
    PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error
    RemoveObject(ctx context.Context, key string) error
    PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error)
}
```

`minioClient` 实现基于 `minio-go/v7`。

### 5.2 Repository 层

```go
type ResourceRepository interface {
    Create(ctx context.Context, r *model.Resource) error
    UpdateStatus(ctx context.Context, id uint64, status uint8) error
}

type TaskRepository interface {
    Create(ctx context.Context, t *model.Task) error
}
```

### 5.3 Service 层

```go
type FileService interface {
    Upload(ctx context.Context, req UploadRequest, userUUID string) (*UploadResult, error)
}

type UploadRequest struct {
    File       multipart.File
    Header     *multipart.FileHeader
    UserID     uint64
    UserUUID   string
}
```

`Upload` 执行流程：

1. 校验文件大小与 MIME 类型
2. 生成 resource UUID 与 storage key
3. 流式上传至 MinIO
4. 创建 Resource 记录（status=1 uploading）
5. 创建 Task 记录（status=pending）
6. 任一步骤失败则回滚 MinIO 对象

### 5.4 Handler 层

```go
func (h *FileHandler) Upload(c *gin.Context) {
    userUUID := c.GetString("user_uuid")
    userID := c.GetUint64("user_id") // set by enriched auth middleware

    file, header, err := c.Request.FormFile("file")
    if err != nil {
        response.BadRequest(c, "FILE_MISSING", "缺少 file 字段")
        return
    }
    defer file.Close()

    result, err := h.svc.Upload(c.Request.Context(), UploadRequest{
        File:     file,
        Header:   header,
        UserID:   userID,
        UserUUID: userUUID,
    })
    if err != nil {
        handleServiceError(c, err)
        return
    }
    response.OK(c, result)
}
```

---

## 6. 关键代码实现

### 6.1 MIME 白名单与任务类型映射

```go
var allowedMimeTypes = map[string]bool{
    "audio/mpeg": true,
    "audio/wav":  true,
    "audio/mp4":  true,
    "video/mp4":  true,
    "video/webm": true,
    "application/pdf": true,
    "text/plain": true,
    "application/msword": true,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
}

func detectTaskType(mime string) string {
    if strings.HasPrefix(mime, "audio/") || strings.HasPrefix(mime, "video/") {
        return "media_parse"
    }
    if mime == "application/pdf" {
        return "pdf_parse"
    }
    return "document_parse"
}
```

### 6.2 流式上传与回滚

```go
func (s *fileService) Upload(ctx context.Context, req UploadRequest) (*UploadResult, error) {
    if req.Header.Size > maxFileSize {
        return nil, apperrors.FileTooLarge("file exceeds 500MB limit")
    }

    mime := req.Header.Header.Get("Content-Type")
    if !allowedMimeTypes[mime] {
        return nil, apperrors.UnsupportedMediaType("unsupported file type")
    }

    resourceUUID := uuid.NewString()
    key := fmt.Sprintf("%s/%s/%s", req.UserUUID, resourceUUID, sanitizeFilename(req.Header.Filename))

    if err := s.storage.PutObject(ctx, key, req.File, req.Header.Size, mime); err != nil {
        return nil, fmt.Errorf("upload to storage: %w", err)
    }

    resource := &model.Resource{
        UUID:       resourceUUID,
        UserID:     req.UserID,
        Name:       req.Header.Filename,
        Type:       detectTaskType(mime),
        Status:     1, // uploading
        StorageKey: key,
        SizeBytes:  req.Header.Size,
        MimeType:   mime,
    }
    if err := s.resourceRepo.Create(ctx, resource); err != nil {
        _ = s.storage.RemoveObject(ctx, key)
        return nil, fmt.Errorf("create resource: %w", err)
    }

    task := &model.Task{
        UUID:       uuid.NewString(),
        ResourceID: resource.ID,
        UserID:     req.UserID,
        Type:       resource.Type,
        Status:     "pending",
    }
    if err := s.taskRepo.Create(ctx, task); err != nil {
        _ = s.storage.RemoveObject(ctx, key)
        return nil, fmt.Errorf("create task: %w", err)
    }

    return &UploadResult{...}, nil
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 缺少 file 字段 | 400 | FILE_MISSING | 缺少文件字段 |
| 文件超过 500MB | 413 | FILE_TOO_LARGE | 文件超过大小限制 |
| MIME 类型不支持 | 415 | FILE_UNSUPPORTED_TYPE | 不支持的文件类型 |
| MinIO 上传失败 | 500 | INTERNAL_ERROR | 文件上传失败 |
| 数据库写入失败 | 500 | INTERNAL_ERROR | 保存资源信息失败 |
| 未认证 | 401 | UNAUTHORIZED | 访问令牌无效 |

---

## 8. Web 端适配要点

- Gateway `POST /api/v1/files/upload` 需启用 CORS：允许 Flutter Web 启动域名、允许 `Content-Type: multipart/form-data` 与 `Authorization` 头、允许 credentials。
- Web 端 Flutter 上传使用 `MultipartFile.fromBytes`，Gateway 对请求体的解析与校验逻辑不变；文件大小仍受服务端 500MB 限制，前端建议限制 ≤100MB。
- Web 端测试使用 `flutter test --platform chrome` 验证 UI 与 mock 上传；集成测试使用 ChromeDriver。

---

## 9. 测试策略

- **单元测试**：MIME 检测、任务类型映射、文件名清理、错误分类
- **集成测试**：MinIO 容器 + MySQL 容器，验证上传成功/大小超限/MIME 不支持/数据库回滚
- **接口测试**：httptest + multipart builder 模拟 401/413/200

---

## 10. 检查清单

- [ ] `FileHandler.Upload` 解析 multipart 并调用 service
- [ ] `FileService.Upload` 完成校验、存储、落库、回滚
- [ ] `MinIOClient` 实现 `ObjectStorage` 接口
- [ ] `ResourceRepository` / `TaskRepository` 创建记录
- [ ] Gin `MaxMultipartMemory` 与最大尺寸限制配置
- [ ] MIME 白名单与任务类型映射
- [ ] 失败时删除已上传对象
- [ ] 单元/集成测试覆盖率 80%+
- [ ] OpenAPI 文档同步更新
