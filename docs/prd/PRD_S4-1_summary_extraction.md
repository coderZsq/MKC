# PRD：[S4-1] 实现全文/章节摘要提取

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S2-3_audio_text_cleaning.md](./PRD_S2-3_audio_text_cleaning.md)、[PRD_S2-4_pdf_text_extraction.md](./PRD_S2-4_pdf_text_extraction.md)、[PRD_S3-5_glm4_kimi_llm.md](./PRD_S3-5_glm4_kimi_llm.md)、[PRD_S4-3_resource_card_summary_tag.md](./PRD_S4-3_resource_card_summary_tag.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-1 |
| **任务名称** | 实现全文/章节摘要提取 |
| **所属史诗** | E8 智能抽取 |
| **故事点** | 3 |
| **优先级** | Should |
| **依赖** | [S2-3 音频文本清洗](./PRD_S2-3_audio_text_cleaning.md)、[S2-4 PDF 文本提取](./PRD_S2-4_pdf_text_extraction.md)、[S3-5 智谱 GLM-4 / Kimi](./PRD_S3-5_glm4_kimi_llm.md) |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为用户，我希望在音频转录或 PDF 解析完成后，系统自动为资源生成「全文摘要」与「章节摘要」，以便我在资源卡片和内容查看页快速了解资源核心内容，而不必通读全文。本任务在转录（S2-3）/解析（S2-4）完成后由 Celery 异步触发，复用 S3-5 的 `LLMClient` 调用智谱 GLM-4 / Kimi 生成摘要，并将结果持久化到独立 `summaries` 表，供 Web 端与 S4-3 资源卡片标签消费。系统边界：输入为 S2-3 清洗后文本与 S2-4 解析 JSON（含 TOC/页码/SRT 时间段），输出为结构化摘要（全文 abstract + 章节 sections）。

---

## 验收标准（AC）

- [ ] **AC-1** 在 S2-3 音频文本清洗或 S2-4 PDF 文本提取完成后，由 Celery 异步触发摘要生成任务，不阻塞主流程
- [ ] **AC-2** 全文摘要：对全文生成 200-300 字中文 abstract，概括核心内容与结论
- [ ] **AC-3** 章节摘要：PDF 用 S2-4 提取的目录/页码划分章节；音频用 S2-2 SRT 时间段或 S3-1 语义分块划分，输出 `sections: [{title, summary, page_range / timestamp_range}]`
- [ ] **AC-4** 长文档采用 map-reduce 策略（分块摘要再汇总），单段 token 上限可配置，控制整体 token 消耗
- [ ] **AC-5** 复用 S3-5 的 `LLMClient`，Prompt 模板使用 Jinja2 渲染，通过 JSON mode / function calling 保证结构化输出
- [ ] **AC-6** 摘要写入独立 `summaries` 表，字段包含 `resource_id, type=full|section, content, section_meta, model, tokens, created_at`
- [ ] **AC-7** 内部接口 `POST /ai/v1/resources/{resource_id}/summarize`（X-Internal-Key）触发摘要；Gateway 暴露 `GET /api/v1/resources/{id}/summary`（Bearer JWT）给前端
- [ ] **AC-8** LLM 失败重试 3 次（tenacity 指数退避）；超长文档分段处理；摘要为空时取前 N 字兜底
- [ ] **AC-9** 权限校验：内部接口校验 `X-Internal-Key`，Gateway 接口校验 `Bearer JWT` 并验证资源归属于当前用户
- [ ] **AC-10** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── api/
│   │   └── summary.py                    # 摘要触发 API（内部）
│   ├── services/
│   │   └── summary/
│   │       ├── __init__.py
│   │       ├── summary_service.py        # 摘要编排
│   │       ├── map_reduce_summarizer.py  # 长文档 map-reduce
│   │       ├── section_splitter.py       # 章节划分（PDF TOC / 音频 SRT）
│   │       └── summary_llm_provider.py   # Prompt + LLM 调用封装
│   ├── models/
│   │   └── summary.py                    # Summary / SectionSummary 模型
│   ├── repositories/
│   │   └── summary_repository.py         # 持久化（MinIO + Gateway 内部接口）
│   ├── prompts/
│   │   ├── full_summary.j2               # 全文摘要 Prompt
│   │   ├── chunk_summary.j2              # 分块摘要 Prompt
│   │   └── section_summary.j2            # 章节摘要 Prompt
│   └── tasks/
│       └── summarize_task.py             # Celery 异步任务
├── config/
│   └── ai.yaml                           # summary 配置段
└── tests/
    ├── unit/test_summary_service.py
    ├── unit/test_map_reduce_summarizer.py
    ├── unit/test_section_splitter.py
    └── integration/test_summary_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| 智谱 GLM-4 / Kimi（S3-5 LLMClient） | - | 摘要生成 |
| Celery | 5.4.x | 异步任务触发 |
| Jinja2 | 3.1.x | Prompt 模板渲染 |
| tiktoken | 0.7.x | token 估算与分块 |
| tenacity | 8.x | LLM 调用重试 |
| pydantic | 2.x | 摘要数据模型校验 |
| MinIO / MySQL（Gateway） | - | 摘要结果存储 |

---

## 技术要点

### 触发请求示例（内部接口）

```json
POST /ai/v1/resources/01922b9c-.../summarize
Headers: X-Internal-Key: <key>
{
  "types": ["full", "section"],
  "source_type": "pdf"
}
```

### 触发响应示例（202 Accepted）

```json
{
  "task_id": "sum-01922b9c-...",
  "status": "pending"
}
```

### Gateway 查询响应示例（前端）

```json
GET /api/v1/resources/01922b9c-.../summary
Authorization: Bearer <jwt>
{
  "success": true,
  "data": {
    "resource_id": "01922b9c-...",
    "full_summary": "本文档介绍了 MKC 多媒体知识库助手的整体架构与核心模块……",
    "sections": [
      {
        "title": "第一章 概述",
        "summary": "本章介绍了系统目标、用户角色与核心场景……",
        "page_range": [1, 3]
      },
      {
        "title": "00:00-05:30 开场",
        "summary": "该时段讨论了会议背景与议程……",
        "timestamp_range": [0.0, 330.0]
      }
    ],
    "model": "glm-4-flash",
    "fallback": false,
    "updated_at": "2026-07-12T10:00:00Z"
  }
}
```

### 数据流

1. S2-3 / S2-4 完成后由 Gateway 回调或事件触发，Celery 拉起 `summarize_task`
2. 从 MinIO 读取清洗后文本（音频）或解析 JSON（PDF，含 TOC 与 pages）
3. 划分章节边界：PDF 用 S2-4 TOC / 页码；音频用 S2-2 SRT 时间段或 S3-1 语义分块
4. 全文摘要：短文档直接调用 LLM；长文档走 map-reduce（分块摘要再汇总）
5. 章节摘要：逐章节调用 LLM 生成，附带 `page_range` / `timestamp_range`
6. 通过 JSON mode / function calling 解析结构化结果，校验 sections schema
7. 全文摘要 JSON 落 MinIO，元数据写入 `summaries` 表，更新任务状态
8. Gateway 暴露 `GET /api/v1/resources/{id}/summary` 给前端与 S4-3 资源卡片标签消费

### 错误处理与降级策略

- **LLM 调用失败**：tenacity 重试 3 次，指数退避（2s / 4s / 8s），重试耗尽标记任务失败
- **超长文档**：按 `chunk_token_limit` 分段，单段 token 上限可配置（默认 3000），重叠 100 tokens
- **摘要为空**：兜底取前 200 字作为摘要，结果标记 `fallback=true`
- **章节划分失败**：降级为整篇全文摘要，`sections` 返回空数组并记录警告
- **LLM 返回非 JSON**：解析失败触发一次重试，仍失败则记录 `SUMMARY_PARSE_FAILED` 并降级
- **LLM 超时**：返回 504，由上层重试或提示用户稍后查看

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LLM 调用慢且 token 费用高 | 任务完成时间变长、成本上升 | map-reduce 控制token；默认 glm-4-flash；mock provider 用于测试 |
| 长文档超出上下文窗口 | 摘要截断或失败 | 强制分段，单段 token 上限可配置 |
| 章节边界识别不准（无 TOC 的 PDF） | 章节摘要语义混乱 | 无 TOC 时降级为全文摘要；S3-1 语义分块兜底 |
| LLM 输出非结构化 JSON | 解析失败 | 使用 JSON mode / function calling，解析失败重试并降级 |
| 摘要生成阻塞主流程 | 用户体验差 | Celery 异步触发，失败不阻塞转录/解析结果 |

---

## Web 端适配

- Web 端通过 `GET /api/v1/resources/{id}/summary` 获取摘要，资源卡片展示全文摘要片段（配合 S4-3 标签）
- 内容查看页按章节折叠展示章节摘要，点击章节可跳转对应页码（PDF）或时间戳（音频）
- 摘要未就绪时展示「生成中」占位；`fallback=true` 时标注「自动摘要」
- 摘要生成失败时展示原文前若干字并提示稍后重试

---

## 备注

- 本任务为 Should 优先级，排期紧张时可先交付全文摘要，章节摘要延后
- 摘要结果与原始文本均需保留，供后续质量评估与重新生成
- 摘要生成需可重入：资源重新处理时清空旧摘要再生成
- Prompt 模板与字数范围需可配置，便于后续调优
