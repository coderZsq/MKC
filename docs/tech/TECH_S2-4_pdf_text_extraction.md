# 技术文档：[S2-4] 集成 pymupdf 实现 PDF 文本提取

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S2-4_pdf_text_extraction.md](../prd/PRD_S2-4_pdf_text_extraction.md)

---

## 1. 文档目标

定义 AI Service 中 PDF 文本提取模块的技术实现：接口契约、PyMuPDF 封装、结构化输出、进度上报与测试方案。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- PyMuPDF 1.24+
- pdfplumber 0.11+（表格提取）
- Celery 5.4+ + Redis
- MinIO Python SDK
- pydantic 2.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/pdf/parse` | Internal API Key | 提交 PDF 解析异步任务 |

### 请求示例

```json
POST /ai/v1/pdf/parse
Headers: X-Internal-Key: <key>
{
  "task_id": "01922b9c-...",
  "resource_id": "01922b9c-...",
  "pdf_url": "minio://resources/.../doc.pdf"
}
```

### 响应示例

```json
{
  "task_id": "01922b9c-...",
  "status": "pending",
  "message": "PDF parse task queued"
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | INVALID_PDF | PDF 损坏或加密 |
| 404 | PDF_NOT_FOUND | 文件不存在 |
| 503 | PARSER_UNAVAILABLE | 解析器不可用 |
| 500 | PDF_PARSE_FAILED | 解析内部错误 |

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
pdf:
  extractor: pymupdf
  ocr_fallback: true            # 无文本层时触发 OCR
  ocr_threshold: 50             # 每页最少字符数
  chunk_size: 10                # 每批处理页数
  progress_interval: 5.0
```

---

## 5. 模块设计

### 5.1 PyMuPDFExtractor

```python
class PyMuPDFExtractor:
    def extract(self, pdf_path: Path) -> PdfDocument: ...
```

### 5.2 PdfParserService

```python
class PdfParserService:
    def parse(self, task: PdfParseTask) -> PdfDocument: ...
```

### 5.3 PdfParseCeleryTask

```python
@app.task(bind=True, max_retries=3)
def run_pdf_parse(self, task_id: str, payload: dict):
    ...
```

---

## 6. 关键代码实现

### 6.1 PyMuPDF 文本提取

```python
import fitz
from pathlib import Path

class PyMuPDFExtractor:
    def extract(self, pdf_path: Path) -> dict:
        doc = fitz.open(str(pdf_path))
        pages = []
        toc = doc.get_toc()
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text()
            blocks = page.get_text("blocks")
            pages.append({
                "page_number": i + 1,
                "text": text,
                "blocks": [
                    {"x": b[0], "y": b[1], "width": b[2], "height": b[3], "text": b[4]}
                    for b in blocks
                ],
            })
        return {
            "total_pages": doc.page_count,
            "toc": [{"level": t[0], "title": t[1], "page": t[2]} for t in toc],
            "pages": pages,
        }
```

### 6.2 扫描件检测

```python
def is_scanned_page(page_text: str, threshold: int = 50) -> bool:
    return len(page_text.strip()) < threshold
```

### 6.3 进度上报

与 S2-1 相同，通过内部接口 PATCH Gateway 任务进度。

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| PDF 加密 | 400 | ENCRYPTED_PDF | 无法解析加密 PDF |
| PDF 损坏 | 400 | CORRUPT_PDF | PDF 文件损坏 |
| 扫描件无文本 | 400 | NO_TEXT_LAYER | 需要 OCR 处理 |
| 解析超时 | 500 | PARSE_TIMEOUT | 解析超时，请重试 |

---

## 8. Web 端适配要点

- PDF 解析结果通过 Gateway 任务详情 API 暴露
- Web 端查看页展示文本大纲与页码
- 点击页码可滚动到对应内容区域

---

## 9. 测试策略

- **单元测试**：`PyMuPDFExtractor` 提取、TOC 解析、扫描件检测
- **集成测试**：提交 PDF 解析任务 → 获取结果 → 验证 pages 结构
- **E2E 测试**：上传 PDF → 等待解析完成 → 查看文本内容
- **Mock 测试**：模拟 PyMuPDF 输出

---

## 10. 检查清单

- [ ] PyMuPDFExtractor 实现
- [ ] PDF 解析 Celery 任务
- [ ] 进度上报
- [ ] 扫描件检测与 OCR 触发
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
