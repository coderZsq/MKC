# PRD：[S2-6] 存储转录/解析结果到对象存储和数据库

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[PRD_S1-3_file_upload_api.md](./PRD_S1-3_file_upload_api.md)、[PRD_S1-5_task_status_api.md](./PRD_S1-5_task_status_api.md)、[PRD_S2-1_faster_whisper_asr.md](./PRD_S2-1_faster_whisper_asr.md)、[PRD_S2-4_pdf_text_extraction.md](./PRD_S2-4_pdf_text_extraction.md)、[TECH_S2-2_srt_generation.md](../tech/TECH_S2-2_srt_generation.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-6 |
| **任务名称** | 存储转录/解析结果到对象存储和数据库 |
| **所属史诗** | E2 文件上传 / E3 任务进度 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S1-5 任务状态 API、S1-3 文件上传 API、S2-1 ASR、S2-4 PDF 解析 |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望转录/解析后的文本、SRT 字幕等结果被持久化保存，以便后续在内容查看页中随时访问。本任务将 ASR/PDF 解析产生的文件与元数据写入 MinIO 与数据库，并对外提供结果查询 API。

---

## 验收标准（AC）

- [ ] **AC-1** ASR 转录文本以 JSON 文件形式写入 MinIO `results/{task_id}/transcript.json`
- [ ] **AC-2** SRT 字幕文件写入 MinIO `results/{task_id}/subtitle.srt`
- [ ] **AC-3** PDF 解析结果以 JSON 文件写入 MinIO `results/{task_id}/parsed.json`
- [ ] **AC-4** task.result 字段记录 MinIO 文件路径与元数据
- [ ] **AC-5** Gateway 提供 `GET /api/v1/tasks/{task_id}/result` 查询结果摘要与文件 URL
- [ ] **AC-6** 文件 URL 支持预签名下载，有效期 1 小时
- [ ] **AC-7** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
gateway/
├── internal/
│   ├── handler/
│   │   └── result_handler.go
│   ├── service/
│   │   ├── result_service.go
│   │   └── minio_service.go
│   └── repository/
│       └── task_repository.go

ai-service/
├── app/
│   ├── services/
│   │   └── result_storage.py
│   └── clients/
│       └── minio_client.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| minio-go | v7.x | Gateway 访问 MinIO |
| minio Python SDK | 7.2.x | AI Service 访问 MinIO |
| GORM | v1.25.x | 更新 task.result |

---

## 技术要点

### task.result 字段结构

```json
{
  "transcript_url": "minio://results/{task_id}/transcript.json",
  "subtitle_url": "minio://results/{task_id}/subtitle.srt",
  "parsed_url": "minio://results/{task_id}/parsed.json",
  "metadata": {
    "total_pages": 12,
    "duration": 3600,
    "word_count": 5000
  }
}
```

### 接口契约

**GET /api/v1/tasks/{task_id}/result**

```json
{
  "success": true,
  "data": {
    "task_id": "...",
    "status": "completed",
    "files": {
      "transcript_url": "https://minio/.../transcript.json?X-Amz-...",
      "subtitle_url": "https://minio/.../subtitle.srt?X-Amz-..."
    },
    "metadata": {...}
  }
}
```

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| MinIO 不可用 | 结果无法存储 | 任务失败，返回 STORAGE_ERROR |
| 大文件上传慢 | 任务完成延迟 | 流式上传，异步通知 |
| 签名 URL 过期 | 客户端下载失败 | 客户端按需刷新，有效期 1 小时 |

---

## Web 端适配

Web 端 Flutter 通过 `GET /api/v1/tasks/{task_id}/result` 获取签名 URL，下载 SRT 或解析文本。签名 URL 过期时重新请求。

---

## 备注

- 原始 ASR/PDF 文件与结果文件分开 bucket，便于生命周期管理
- 结果文件按 task_id 组织，便于清理
- 同一资源重新解析时覆盖旧结果或生成新版本（后续扩展）
