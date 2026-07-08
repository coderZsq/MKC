# PRD：[S2-4] 集成 pymupdf 实现 PDF 文本提取

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[TECH_S0-8_python_ai_service_skeleton.md](../tech/TECH_S0-8_python_ai_service_skeleton.md)、[TECH_S2-6_result_storage.md](../tech/TECH_S2-6_result_storage.md)、[TECH_S2-5_pdf_ocr.md](../tech/TECH_S2-5_pdf_ocr.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-4 |
| **任务名称** | 集成 pymupdf 实现 PDF 文本提取 |
| **所属史诗** | E5 PDF 解析 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S0-8 Python AI Service 骨架、S1-5 任务状态 API |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望上传的 PDF 文件被自动解析成结构化文本，以便后续检索与问答。本任务在 AI Service 中集成 PyMuPDF，提取文本、目录、页码与基础元数据，并生成 Markdown 或 JSON 结构输出。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供 `POST /ai/v1/pdf/parse` 异步任务接口，接收 resource_id 与 PDF URL
- [ ] **AC-2** 使用 PyMuPDF 提取每页纯文本并保留页码
- [ ] **AC-3** 输出包含文档目录（TOC）、标题层级（如果有）、页面块信息
- [ ] **AC-4** 输出 JSON 结构：`pages[{page_number, text, blocks[{x, y, text}]}]`
- [ ] **AC-5** 解析过程中定期上报 `progress` 到 Gateway
- [ ] **AC-6** 失败时返回明确错误码，任务进入 failed 状态
- [ ] **AC-7** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── api/
│   │   └── pdf.py                 # PDF 解析 API
│   ├── services/
│   │   ├── pdf_parser.py          # PDF 解析 orchestration
│   │   └── pymupdf_extractor.py   # PyMuPDF 封装
│   ├── models/
│   │   └── pdf_document.py        # 结构化文档模型
│   └── tasks/
│       └── pdf_parse_task.py      # Celery 任务
└── tests/
    ├── unit/test_pymupdf_extractor.py
    └── integration/test_pdf_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| PyMuPDF | 1.24.x | PDF 文本与元数据提取 |
| pdfplumber | 0.11.x | 表格提取（可选） |
| Celery | 5.4.x | 异步任务 |

---

## 技术要点

### 输出格式示例

```json
{
  "resource_id": "...",
  "total_pages": 12,
  "toc": [
    {"level": 1, "title": "第一章", "page": 1}
  ],
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "blocks": [
        {"x": 50, "y": 100, "text": "标题"}
      ]
    }
  ]
}
```

### 解析流程

1. 从 MinIO 下载 PDF 到临时文件
2. 使用 PyMuPDF 打开文档，获取元数据与 TOC
3. 逐页提取文本块，保留坐标与页码
4. 合并为 pages 数组
5. 上传 JSON 结果到 MinIO，更新 task.result

### 错误处理

- PDF 加密或损坏：返回 400
- 扫描件无文本层：提示使用 S2-5 PDF OCR
- 提取超时：按页重试

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 扫描件 PDF 无文本层 | 提取为空 | 标记为需 OCR，触发 S2-5 |
| 大 PDF 内存占用高 | 解析失败 | 按页流式处理，限制并发 |
| 复杂排版文本顺序错乱 | 阅读体验差 | 后续 S3 分块时基于坐标重排 |

---

## Web 端适配

Web 端内容查看页以 Markdown 或结构树形式展示 PDF 解析文本。页码作为锚点，支持点击跳转到 PDF 对应页（后续 S4 引用跳转）。

---

## 备注

- 解析结果原始 JSON 保留，S3 分块与 Embedding 使用
- 表格与图片提取在 S4 或后续扩展
- 扫描件检测逻辑：统计每页文本字符数，低于阈值时触发 OCR 建议
