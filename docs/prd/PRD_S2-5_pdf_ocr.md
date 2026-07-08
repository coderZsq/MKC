# PRD：[S2-5] PDF 扫描件 OCR（可选）

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[PRD_S2-4_pdf_text_extraction.md](./PRD_S2-4_pdf_text_extraction.md)、[TECH_S2-4_pdf_text_extraction.md](../tech/TECH_S2-4_pdf_text_extraction.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-5 |
| **任务名称** | PDF 扫描件 OCR（可选） |
| **所属史诗** | E5 PDF 解析 |
| **故事点** | 2 |
| **优先级** | Could |
| **依赖** | S2-4 PDF 文本提取 |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望上传的扫描件 PDF 也能被识别成文字，以便纳入知识库检索。本任务在 PDF 文本提取为空时，使用 PaddleOCR 对 PDF 每页渲染图像并执行 OCR，输出结构化文本。

---

## 验收标准（AC）

- [ ] **AC-1** 当 S2-4 检测到无文本层时，自动触发 OCR 流程
- [ ] **AC-2** 使用 PaddleOCR 对 PDF 每页进行文字识别
- [ ] **AC-3** OCR 结果按页码组织，输出与 S2-4 相同的 JSON 结构
- [ ] **AC-4** 支持中文与英文混合识别
- [ ] **AC-5** OCR 结果写入 MinIO，更新 task.result
- [ ] **AC-6** 失败时返回 OCR_FAILED 并允许手动重试
- [ ] **AC-7** 单元测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── services/
│   │   ├── ocr_service.py         # OCR 编排
│   │   └── paddle_ocr_engine.py   # PaddleOCR 封装
│   └── utils/
│       └── pdf_renderer.py        # PDF 转图片
└── tests/
    └── unit/test_ocr_engine.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| paddleocr | 2.7+ | OCR 引擎 |
| paddlepaddle | 2.6+ | PaddleOCR 运行时 |
| pymupdf | 1.24+ | PDF 渲染为图片 |
| Pillow | 10+ | 图像处理 |

---

## 技术要点

### OCR 流程

1. PyMuPDF 渲染每页为 PNG（300 DPI）
2. PaddleOCR 识别文字与坐标
3. 按页汇总文本块
4. 输出 pages 结构

### 输出格式

与 S2-4 相同，blocks 中增加 OCR 置信度。

### 性能优化

- 仅对无文本层页面执行 OCR
- 可配置并发页数，避免内存溢出

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| PaddleOCR 模型体积大 | 环境搭建慢 | 首次下载后缓存，CI 预下载 |
| 中文识别率低 | 解析质量差 | 后续 S2-3 文本清洗可辅助 |
| 大分辨率 PDF 占用显存 | 服务崩溃 | 限制 DPI 与并发 |

---

## Web 端适配

Web 端内容查看页对 OCR 结果与正常 PDF 文本无差别展示。用户可看到 OCR 置信度提示（可选）。

---

## 备注

- 本任务为 Could 优先级，排期紧张时可延后
- 可与 S2-4 合并为 PDF 解析任务，OCR 作为 fallback 分支
- 后续可替换为更易部署的 OCR 方案或云端 API
