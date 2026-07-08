# 技术文档：[S2-6] 存储转录/解析结果到对象存储和数据库

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：后端/AI 工程师
> 关联 PRD：[../prd/PRD_S2-6_result_storage.md](../prd/PRD_S2-6_result_storage.md)

---

## 1. 文档目标

定义转录/解析结果在 MinIO 与数据库中的持久化方案，包括 Gateway 查询 API、签名 URL 生成与 AI Service 上传逻辑。

---

## 2. 技术栈

- Go 1.22+ / Gin 1.10.x
- GORM 1.25.x
- minio-go v7.x
- Python 3.11+
- MinIO Python SDK 7.2.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api/v1/tasks/{task_id}/result` | Bearer JWT | 查询任务结果与签名 URL |

### 请求示例

```text
GET /api/v1/tasks/01922b9c-.../result
Authorization: Bearer <access_token>
```

### 响应示例

```json
{
  "success": true,
  "data": {
    "task_id": "01922b9c-...",
    "status": "completed",
    "files": {
      "transcript_url": "https://minio/.../transcript.json?X-Amz-...",
      "subtitle_url": "https://minio/.../subtitle.srt?X-Amz-...",
      "parsed_url": "https://minio/.../parsed.json?X-Amz-..."
    },
    "metadata": {
      "total_pages": 12
    }
  }
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 404 | TASK_NOT_FOUND | 任务不存在或无权访问 |
| 400 | TASK_NOT_COMPLETED | 任务未完成 |
| 500 | STORAGE_ERROR | 无法生成签名 URL |

---

## 4. 配置

新增 Gateway `config/gateway.yaml`：

```yaml
minio:
  endpoint: "minio:9000"
  bucket: "results"
  presigned_expiry: 1h
  use_ssl: false
```

---

## 5. 模块设计

### 5.1 Gateway

- `ResultHandler`: HTTP 入口
- `ResultService`: 签名 URL 生成与元数据组装
- `MinioService`: MinIO 客户端封装
- `TaskRepository`: 读取 task.result

### 5.2 AI Service

- `ResultStorage`: 上传结果文件到 MinIO
- `MinioClient`: 上传与路径管理

---

## 6. 关键代码实现

### 6.1 Go 签名 URL 生成

```go
func (s *minioService) PresignedGetURL(ctx context.Context, objectKey string, expiry time.Duration) (string, error) {
    reqParams := make(url.Values)
    reqParams.Set("response-content-disposition", "attachment")
    return s.client.PresignedGetObject(ctx, s.bucket, objectKey, expiry, reqParams)
}
```

### 6.2 Python 上传结果

```python
def upload_result(self, task_id: str, file_name: str, content: bytes, content_type: str) -> str:
    object_name = f"{task_id}/{file_name}"
    self.client.put_object(
        bucket_name=self.bucket,
        object_name=object_name,
        data=io.BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name
```

### 6.3 更新 task.result

```python
task.result = {
    "transcript_url": f"minio://{self.bucket}/{task_id}/transcript.json",
    "subtitle_url": f"minio://{self.bucket}/{task_id}/subtitle.srt",
    "metadata": {...}
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 任务不存在 | 404 | TASK_NOT_FOUND | 任务不存在 |
| 任务未完成 | 400 | TASK_NOT_COMPLETED | 任务尚未完成 |
| 签名 URL 生成失败 | 500 | PRESIGNED_URL_FAILED | 无法生成下载链接 |
| MinIO 上传失败 | 500 | UPLOAD_FAILED | 结果上传失败 |

---

## 8. Web 端适配要点

- Web 端 Flutter 下载结果文件时，使用签名 URL 直接请求 MinIO 或 Gateway 代理
- 签名 URL 过期时，调用 `GET /api/v1/tasks/{task_id}/result` 刷新
- 大文件下载需使用 `dio` 流式读取，避免内存溢出

---

## 9. 测试策略

- **Gateway 单元测试**：签名 URL 生成、任务权限校验
- **Gateway 集成测试**：任务完成 → 查询结果 → 下载文件
- **AI Service 集成测试**：生成结果 → 上传 MinIO → 更新 task
- **E2E 测试**：上传文件 → 处理完成 → 获取结果下载

---

## 10. 检查清单

- [ ] Gateway 结果查询 API
- [ ] MinIO 签名 URL 生成
- [ ] AI Service 结果上传
- [ ] task.result 更新
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
