# S4-1 测试用例：实现全文/章节摘要提取

## 1. 范围与目标

验证全文/章节摘要提取服务：全文摘要生成、章节划分与摘要、长文档 map-reduce、Jinja2 Prompt 与 JSON mode 结构化输出、`summaries` 表持久化、Celery 异步触发与失败重试、权限校验、降级兜底与代码质量。

## 2. 测试环境

- Python 3.11+
- Celery 5.4+ + Redis 7.x（eager 模式用于单测）
- 智谱 GLM-4 / Kimi API key（集成测试）/ mock provider（CI）
- tiktoken 0.7.x、Jinja2 3.1.x、tenacity 8.x
- 测试 PDF 解析 JSON（含 TOC/pages）与音频 SRT segments 数据

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-1-001 | Functional | Unit | P0 | 全文摘要生成且字数在 200-300 | 提供 PDF 全文文本 | 调用 summarize_full | 返回摘要且字数在 200-300 之间 | PRD AC-2 |
| MKC-TC-S4-1-002 | Functional | Unit | P0 | 章节摘要按 PDF TOC 划分 | 提供 S2-4 解析 JSON（含 toc/pages） | 调用 section_splitter.split_pdf | sections 含 title、page_range 且页码连续 | PRD AC-3 |
| MKC-TC-S4-1-003 | Functional | Unit | P0 | 章节摘要按音频 SRT 时间段划分 | 提供 S2-2 SRT segments | 调用 section_splitter.split_audio | sections 含 title、timestamp_range 且时间连续 | PRD AC-3 |
| MKC-TC-S4-1-004 | Functional | Integration | P0 | 长文档 map-reduce 分块汇总 | 文本 token 数 > chunk_token_limit | 调用 map_reduce_summarizer.summarize | 先分块摘要再汇总，输出全文摘要 | PRD AC-4 |
| MKC-TC-S4-1-005 | Functional | Unit | P1 | LLM JSON mode 输出被正确解析 | mock LLM 返回 {"summary":"..."} | 调用 summarize_full | 解析出 summary 字段 | PRD AC-5 |
| MKC-TC-S4-1-006 | Functional | Unit | P1 | Jinja2 Prompt 模板渲染正确 | 模板文件存在 | 渲染 full_summary.j2 | 含字数范围与文档内容占位 | PRD AC-5 |
| MKC-TC-S4-1-007 | Functional | Integration | P0 | 摘要写入 summaries 表 | mock LLM + Gateway 内部接口 | 调用 service.generate 后检查 repo.save | MinIO 上传 summary.json 且 Gateway 收到持久化请求 | PRD AC-6 |
| MKC-TC-S4-1-008 | Functional | Integration | P0 | Celery 异步触发摘要任务 | S2-3/S2-4 完成事件 | 派发 run_summarize 任务 | 任务进入 running 且不阻塞主流程 | PRD AC-1 |
| MKC-TC-S4-1-009 | Functional | Integration | P1 | 内部 POST 触发接口返回 task_id | 资源已就绪 | 调用 POST /ai/v1/resources/{id}/summarize | 返回 202 与 task_id | PRD AC-7 |
| MKC-TC-S4-1-010 | Functional | Integration | P1 | Gateway GET 查询接口返回摘要 | 摘要已生成 | 调用 GET /api/v1/resources/{id}/summary | 返回 full_summary 与 sections | PRD AC-7 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-1-011 | Security | Integration | P0 | 内部接口校验 X-Internal-Key | 接口已部署 | 不带/带错误 Key 调用 POST /ai/v1/.../summarize | 返回 401 INTERNAL_AUTH_FAILED | PRD AC-9 |
| MKC-TC-S4-1-012 | Security | Integration | P0 | Gateway 接口校验 Bearer JWT | 接口已部署 | 不带/带无效 JWT 调用 GET /api/v1/.../summary | 返回 401 UNAUTHORIZED | PRD AC-9 |
| MKC-TC-S4-1-013 | Security | Integration | P1 | 资源归属校验 | 用户 A 的资源 | 用户 B 的 JWT 查询 | 返回 404 RESOURCE_NOT_FOUND | PRD AC-9 |
| MKC-TC-S4-1-014 | Security | Static | P1 | 无硬编码 LLM API Key | 代码存在 | 全局搜索 key 字面量 | 仅 .env / 配置占位出现 | 安全基线 |
| MKC-TC-S4-1-015 | Security | Integration | P1 | LLM 失败日志不泄露 key | 模拟 LLM 异常 | 查看错误日志与响应 | 无 API Key 泄露 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-1-016 | Negative | Unit | P0 | LLM 失败重试 3 次 | mock LLM 抛异常 | 调用 summarize_full | tenacity 重试 3 次后抛出 | PRD AC-8 |
| MKC-TC-S4-1-017 | Negative | Integration | P1 | 重试耗尽标记任务失败 | mock LLM 持续失败 | 执行 run_summarize | 任务标记 failed 且上报 Gateway | PRD AC-8 |
| MKC-TC-S4-1-018 | Negative | Unit | P1 | 超长文档分段成功 | 文本 token 数远超 limit | 调用 _split_chunks | 切分为多段且重叠正确 | PRD AC-8 |
| MKC-TC-S4-1-019 | Negative | Unit | P0 | 摘要为空兜底取前 200 字 | mock LLM 返回空 summary | 调用 _safe_full | 返回前 200 字且 fallback=true | PRD AC-8 |
| MKC-TC-S4-1-020 | Negative | Unit | P1 | LLM 返回非 JSON 解析失败降级 | mock LLM 返回纯文本 | 调用 _parse_json | 抛出 SUMMARY_PARSE_FAILED | TECH 7 |
| MKC-TC-S4-1-021 | Negative | Unit | P1 | 章节划分失败降级为全文摘要 | PDF 无 TOC | 调用 service.generate | sections 为空，仅返回全文摘要 | PRD AC-8 |
| MKC-TC-S4-1-022 | Negative | Integration | P2 | 重复触发返回 409 | 摘要任务进行中 | 再次调用 POST /ai/v1/.../summarize | 返回 409 SUMMARY_IN_PROGRESS | TECH 3 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-1-023 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-10 |
| MKC-TC-S4-1-024 | Functional | Static | P1 | ruff 检查通过 | 代码存在 | 运行 ruff check | 0 issues | 工程规范 |
| MKC-TC-S4-1-025 | Functional | Static | P1 | mypy 类型检查通过 | 代码存在 | 运行 mypy app/ | 0 errors | 工程规范 |
| MKC-TC-S4-1-026 | Security | Static | P1 | 无硬编码 secrets | 代码存在 | 静态扫描 secret | 无硬编码密钥 | 安全基线 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-1-027 | Compatibility | Integration | P1 | GLM-4 与 Kimi provider 均可生成摘要 | 配置两个 provider | 分别切换 provider 调用 | 均返回合法摘要 | PRD AC-5 |
| MKC-TC-S4-1-028 | Performance | Integration | P2 | 大文档（>50 页）摘要生成在超时内完成 | 准备 50+ 页 PDF | 触发摘要并计时 | 单次 LLM 调用 < 60s，整体完成 | TECH 4 |
| MKC-TC-S4-1-029 | Compatibility | Widget | P2 | Web 端展示全文摘要与章节折叠 | 摘要已生成 | 前端加载 summary 接口 | 全文摘要展示，章节可折叠跳转 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] 全文摘要生成（200-300 字）
- [ ] 章节摘要生成（PDF TOC / 音频 SRT）
- [ ] 长文档 map-reduce
- [ ] Jinja2 Prompt 渲染
- [ ] JSON mode 结构化输出解析
- [ ] summaries 表持久化
- [ ] Celery 异步触发
- [ ] 内部触发接口 + Gateway 查询接口
- [ ] LLM 失败重试 3 次
- [ ] 超长文档分段
- [ ] 空摘要兜底
- [ ] 章节划分失败降级
- [ ] 权限校验（X-Internal-Key / Bearer JWT / 资源归属）
- [ ] 覆盖率 80%+
- [ ] ruff / mypy 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
