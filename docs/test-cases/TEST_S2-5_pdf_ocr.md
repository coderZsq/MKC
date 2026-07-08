# S2-5 测试用例：PDF 扫描件 OCR（可选）

## 1. 范围与目标

验证 PDF 扫描件 OCR 功能：触发条件、图像渲染、文字识别、结构化输出与失败处理。

## 2. 测试环境

- Python 3.11+
- PaddleOCR / paddlepaddle 已安装
- PyMuPDF 已安装
- 扫描件 PDF 测试文件

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-5-001 | Functional | Unit | P0 | PDF 页面渲染为图片 | 提供 PDF | 调用 render_pdf_page | 输出 PNG 文件 | PRD AC-2 |
| MKC-TC-S2-5-002 | Functional | Unit | P0 | PaddleOCR 识别文字 | 提供图片 | 调用 recognize | 返回文字块列表 | PRD AC-2 |
| MKC-TC-S2-5-003 | Functional | Integration | P0 | 扫描 PDF 触发 OCR 流程 | 提供扫描 PDF | 调用 PDF 解析 | 输出 OCR 结果 | PRD AC-1 |
| MKC-TC-S2-5-004 | Functional | Unit | P1 | 输出 pages 结构 | 提供 OCR 结果 | 调用 OcrService | 结构与 S2-4 一致 | PRD AC-3 |
| MKC-TC-S2-5-005 | Functional | Integration | P1 | 中英文混合识别 | 提供混合文档 | 解析 | 中英文均被识别 | PRD AC-4 |
| MKC-TC-S2-5-006 | Functional | Integration | P1 | OCR 结果写入 MinIO | 解析完成 | 检查 task.result | 结果 URL 可访问 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-5-007 | Security | Static | P1 | 无硬编码 OCR 模型路径 | 代码存在 | 全局搜索 | 仅配置出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-5-008 | Negative | Integration | P0 | OCR 引擎加载失败返回 503 | 模型缺失 | 调用解析 | 返回 OCR_UNAVAILABLE | PRD AC-6 |
| MKC-TC-S2-5-009 | Negative | Integration | P1 | 全部页面无文字返回错误 | 提供空白 PDF | 调用解析 | 返回 OCR_NO_TEXT | PRD AC-6 |
| MKC-TC-S2-5-010 | Negative | Unit | P1 | 单页 OCR 失败不中断整体 | 模拟单页失败 | 调用 OcrService | 其他页仍返回 | 容错 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-5-011 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S2-5-012 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-5-013 | Compatibility | Widget | P2 | Web 端查看 OCR 结果 | 解析完成 | 打开内容页 | 文本正常展示 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] PDF 渲染
- [ ] OCR 文字识别
- [ ] 扫描件触发 OCR
- [ ] 输出结构化 pages
- [ ] 结果写入 MinIO
- [ ] 错误处理
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
