# S2-4 测试用例：集成 pymupdf 实现 PDF 文本提取

## 1. 范围与目标

验证 PDF 文本提取链路：接口响应、文本提取、目录解析、结构化输出、扫描件检测、进度上报与错误处理。

## 2. 测试环境

- Python 3.11+
- PyMuPDF 1.24+
- Redis + Celery Worker
- MinIO 可用
- 测试 PDF 文件（含目录、纯文本、扫描件）

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-4-001 | Functional | Integration | P0 | 提交 PDF 解析任务成功 | 提供 PDF URL | POST /ai/v1/pdf/parse | 返回 task_id，状态 pending | PRD AC-1 |
| MKC-TC-S2-4-002 | Functional | Unit | P0 | 提取每页文本 | 提供 5 页 PDF | 调用 PyMuPDFExtractor | 每页 text 非空 | PRD AC-2 |
| MKC-TC-S2-4-003 | Functional | Unit | P0 | 保留页码 | 提供 PDF | 提取 pages | page_number 从 1 开始 | PRD AC-2 |
| MKC-TC-S2-4-004 | Functional | Unit | P1 | 提取目录 TOC | 提供带目录 PDF | 调用 extract | toc 非空 | PRD AC-3 |
| MKC-TC-S2-4-005 | Functional | Integration | P1 | 输出 JSON 结构正确 | 解析完成 | 检查 task.result | 含 pages / total_pages / toc | PRD AC-4 |
| MKC-TC-S2-4-006 | Functional | Integration | P1 | 进度上报到 Gateway | 运行任务 | 查看任务进度 | progress 递增 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-4-007 | Security | Integration | P0 | 缺少内部 Key 拒绝访问 | 无 Key | POST /ai/v1/pdf/parse | 返回 401 | TECH 3 |
| MKC-TC-S2-4-008 | Security | Static | P1 | 无硬编码 MinIO 凭证 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-4-009 | Negative | Integration | P0 | 加密 PDF 返回 400 | 提供加密 PDF | 提交任务 | 返回 ENCRYPTED_PDF | PRD AC-6 |
| MKC-TC-S2-4-010 | Negative | Integration | P1 | 损坏 PDF 返回 400 | 提供损坏 PDF | 提交任务 | 返回 CORRUPT_PDF | PRD AC-6 |
| MKC-TC-S2-4-011 | Negative | Unit | P1 | 扫描页检测正确 | 提供扫描页 | 调用 is_scanned_page | 返回 true | PRD 阻塞风险 |
| MKC-TC-S2-4-012 | Negative | Integration | P1 | 无文本层时触发 OCR 建议 | 提供扫描 PDF | 提交任务 | 返回 NO_TEXT_LAYER 或触发 S2-5 | PRD 备注 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-4-013 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S2-4-014 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-4-015 | Compatibility | Widget | P2 | Web 端查看 PDF 解析文本 | 任务完成 | 打开内容查看页 | 文本按页展示 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] PDF 解析任务提交
- [ ] 每页文本提取
- [ ] 页码保留
- [ ] TOC 提取
- [ ] 扫描件检测
- [ ] 进度上报
- [ ] 错误处理
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
