# S4-5 测试用例：答案引用溯源（时间戳/页码）

## 1. 范围与目标

验证 AI Service 答案引用溯源模块：Prompt 引用指示、`[^n]` 标记映射、音频时间戳与 PDF 页码引用、幻觉引用剔除、SSE `citation` 事件下发、权限校验、Flutter `CitationCard` 渲染与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- pydantic 2.x
- Jinja2 3.1+
- pytest, pytest-cov
- mock RetrievalService 与 LLM 流式客户端
- Flutter 3.x（Widget 测试，可选）

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-5-001 | Functional | Unit | P0 | CitationFormatter 将 [^n] 映射到 chunk metadata | 提供带 [^1][^2] 的答案与对应 chunks | 调用 CitationFormatter.format | citations 含 chunk_id/resource_id/score 且序号正确 | PRD AC-2 |
| MKC-TC-S4-5-002 | Functional | Unit | P0 | Prompt 模板包含引用指示 | 提供 rag_citation.txt | 渲染 PromptBuilder.build | 模板含 [^n] 指示与片段序号 | PRD AC-1 |
| MKC-TC-S4-5-003 | Functional | Unit | P0 | 音频时间戳引用 mm:ss 格式化 | chunk metadata 含 timestamp_start/end | 调用 format_timestamp | 输出 mm:ss 格式 | PRD AC-3 |
| MKC-TC-S4-5-004 | Functional | Unit | P0 | PDF 页码 + snippet 引用 | chunk metadata 含 page | 调用 CitationFormatter.format | citation 含 page 与截断 snippet | PRD AC-4 |
| MKC-TC-S4-5-005 | Functional | Unit | P0 | CitationService 编排格式化与校验 | 提供答案、chunks、授权集合 | 调用 build_citations | 返回答案与有序 citations | PRD AC-2, AC-5 |
| MKC-TC-S4-5-006 | Functional | Integration | P0 | SSE citation 事件字段与顺序 | mock 检索与 LLM | 调用 stream_answer 收集事件 | citation 事件含全部字段且位于 done 之前 | PRD AC-6 |
| MKC-TC-S4-5-007 | Functional | Unit | P1 | 同一标记多处引用复用序号 | 答案含多个 [^1] | 调用 CitationFormatter.format | citations 仅含一条 index=1 | PRD AC-2 |
| MKC-TC-S4-5-008 | Functional | Widget | P1 | Flutter CitationCard 渲染来源 | 提供 citation 数据 | 渲染 CitationCard | audio 显示 mm:ss，pdf 显示第 N 页 | PRD AC-7 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-5-009 | Security | Integration | P0 | 缺少 Internal Key 拒绝访问 | 请求头无 Key | POST /ai/v1/qa/stream | 返回 401 | TECH 3 |
| MKC-TC-S4-5-010 | Security | Unit | P0 | 越权资源不进入引用列表 | chunks 含未授权 resource_id | 调用 CitationValidator.validate | 越权引用被剔除 | PRD AC-8 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-5-011 | Negative | Unit | P1 | LLM 未生成引用时 citation_count=0 | 答案无 [^n] 标记 | 调用 build_citations | citations 为空，done.citation_count=0 | PRD 降级策略 |
| MKC-TC-S4-5-012 | Negative | Unit | P1 | 越序标记被剔除 | 答案含 [^3] 但仅 2 个片段 | 调用 CitationFormatter.format | [^3] 被剔除并记录日志 | PRD AC-5 |
| MKC-TC-S4-5-013 | Negative | Unit | P1 | metadata 缺失时引用降级 | chunk 无 page/timestamp | 调用 CitationFormatter.format | citation 仅返回 resource_id 与 score，不报错 | PRD 降级策略 |
| MKC-TC-S4-5-014 | Negative | Unit | P2 | 引用数超上限截断 | 答案含 10 个有效标记，max=8 | 调用 CitationValidator.validate | 仅保留前 8 条 | PRD AC-5 |
| MKC-TC-S4-5-015 | Negative | Integration | P1 | LLM 超时返回 504 | mock LLM 超时 | 调用 stream_answer | 返回 LLM_TIMEOUT | TECH 7 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-5-016 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-9 |
| MKC-TC-S4-5-017 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |
| MKC-TC-S4-5-018 | Security | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-5-019 | Compatibility | Unit | P2 | 音频与 PDF resource_type 兼容 | 两种类型 chunks | 调用 build_citations | 分别返回 timestamp 与 page | PRD AC-3, AC-4 |
| MKC-TC-S4-5-020 | Performance | Unit | P2 | 引用映射耗时 < 100ms | 提供长答案与多 chunks | 调用 build_citations | 耗时 < 100ms | 性能基线 |
| MKC-TC-S4-5-021 | Compatibility | Widget | P2 | CitationCard 与 [^n] 脚注联动 | 答案含 [^1] 与对应 citation | 渲染消息与卡片 | 卡片序号与脚注一致 | PRD AC-7 |

## 4. 测试执行清单

- [ ] CitationFormatter 标记映射
- [ ] CitationValidator 剔除与截断
- [ ] CitationService 编排
- [ ] 音频时间戳 / PDF 页码引用
- [ ] Prompt 引用指示
- [ ] SSE citation 事件与顺序
- [ ] 权限与越权过滤
- [ ] 无引用与异常降级
- [ ] Flutter CitationCard 渲染
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
