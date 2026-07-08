# 技术文档：[S2-5] PDF 扫描件 OCR（可选）

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S2-5_pdf_ocr.md](../prd/PRD_S2-5_pdf_ocr.md)

---

## 1. 文档目标

定义 PDF 扫描件 OCR 的技术实现：触发条件、PaddleOCR 封装、PDF 渲染、结构化输出与测试方案。

---

## 2. 技术栈

- Python 3.11+
- PaddleOCR 2.7+
- paddlepaddle 2.6+
- PyMuPDF 1.24+
- Pillow 10+

---

## 3. 接口契约

OCR 为 PDF 解析的内部 fallback 分支，不直接暴露 HTTP 接口。

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
ocr:
  enabled: true
  engine: paddleocr
  lang: ch
  dpi: 300
  max_pages_in_memory: 5
  use_gpu: false
```

---

## 5. 模块设计

### 5.1 PaddleOCREngine

```python
class PaddleOCREngine:
    def __init__(self, lang: str = "ch", use_gpu: bool = False): ...
    def recognize(self, image_path: Path) -> list[OcrBlock]: ...
```

### 5.2 PdfRenderer

```python
class PdfRenderer:
    def render_pages(self, pdf_path: Path, dpi: int = 300) -> Iterator[Image]: ...
```

### 5.3 OcrService

```python
class OcrService:
    def process_pdf(self, pdf_path: Path) -> PdfDocument: ...
```

---

## 6. 关键代码实现

### 6.1 PDF 渲染为图片

```python
import fitz
from pathlib import Path

def render_pdf_page(pdf_path: Path, page_num: int, dpi: int = 300) -> Path:
    doc = fitz.open(str(pdf_path))
    page = doc.load_page(page_num)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    output = Path(f"/tmp/{pdf_path.stem}_page_{page_num}.png")
    pix.save(str(output))
    return output
```

### 6.2 PaddleOCR 识别

```python
from paddleocr import PaddleOCR

class PaddleOCREngine:
    def __init__(self, lang: str = "ch", use_gpu: bool = False):
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu)

    def recognize(self, image_path: Path):
        result = self.ocr.ocr(str(image_path), cls=True)
        blocks = []
        for line in result[0] or []:
            bbox, (text, score) = line
            blocks.append({
                "x": bbox[0][0], "y": bbox[0][1],
                "text": text, "confidence": score,
            })
        return blocks
```

### 6.3 OCR 触发条件

在 PdfParserService 中：

```python
if self.is_scanned_document(doc):
    if self.config.ocr.enabled:
        return self.ocr_service.process_pdf(pdf_path)
    raise PdfParseError("NO_TEXT_LAYER")
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| OCR 引擎加载失败 | 503 | OCR_UNAVAILABLE | OCR 引擎不可用 |
| 单页 OCR 失败 | 500 | OCR_PAGE_FAILED | 某页 OCR 失败 |
| 全部页面 OCR 为空 | 400 | OCR_NO_TEXT | 无法识别文字 |

---

## 8. Web 端适配要点

- OCR 结果与正常文本统一格式返回
- Web 端展示时可选显示 OCR 置信度标签
- 失败时提供手动重试按钮

---

## 9. 测试策略

- **单元测试**：PDF 渲染、OCR 结果解析、触发条件
- **集成测试**：扫描 PDF → OCR → 结构化输出
- **Mock 测试**：模拟 PaddleOCR 返回结果

---

## 10. 检查清单

- [ ] PaddleOCR 引擎封装
- [ ] PDF 渲染为图片
- [ ] OCR 触发条件集成
- [ ] 结果结构化输出
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
