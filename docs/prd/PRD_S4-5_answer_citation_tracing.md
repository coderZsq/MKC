# PRD：[S4-5] 答案引用溯源（时间戳/页码）

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)、[PRD_S3-6_sse_qa_api.md](./PRD_S3-6_sse_qa_api.md)、[PRD_S3-7_flutter_chat_page.md](./PRD_S3-7_flutter_chat_page.md)、[PRD_S4-6_citation_jump_navigation.md](./PRD_S4-6_citation_jump_navigation.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-5 |
| **任务名称** | 答案引用溯源（时间戳/页码） |
| **所属史诗** | E6 知识库检索 |
| **故事点** | 5 |
| **优先级** | Should |
| **依赖** | S3-1 文本分块、S3-4 向量检索+上下文组装、S3-6 SSE 问答 API |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为用户，当我阅读 AI 生成的答案时，我希望答案中带有可溯源的引用标记 [^1][^2]，并能查看每个引用对应的具体来源——音频资源显示 SRT 时间戳、PDF 资源显示页码与片段，以便我快速核验答案依据、跳转到原始素材。本任务在 AI Service 中新增 `CitationService`，通过 Prompt 指示 LLM 插入引用标记，后处理将标记映射到 S3-1/S3-4 保留的 chunk metadata，校验剔除无依据引用（幻觉防护），并复用 S3-6 SSE 问答链路下发结构化 `citation` 事件，供 S3-7 Flutter 端 `CitationCard` 展示、S4-6 跳转导航消费。

---

## 验收标准（AC）

- [ ] **AC-1** Prompt 模板指示 LLM 在答案中插入 `[^n]` 引用标记，标记编号与上下文片段序号一一对应
- [ ] **AC-2** 后处理 `CitationFormatter` 将答案中的 `[^n]` 标记映射到对应 chunk metadata（chunk_id、resource_id、page 或 timestamp_start/end、score），生成结构化 citations 列表
- [ ] **AC-3** 音频资源引用展示 SRT 时间戳（timestamp_start/end），支持 `mm:ss` 格式化输出
- [ ] **AC-4** PDF 资源引用展示页码（page）与原文片段（snippet）
- [ ] **AC-5** `CitationValidator` 校验每个引用标记均有对应 chunk，剔除无上下文依据的引用标记（幻觉防护），并在日志中记录被剔除标记
- [ ] **AC-6** SSE 问答链路新增 `citation` 事件，包含字段：message_id、chunk_id、resource_id、resource_type、page/timestamp_start/timestamp_end、score、snippet
- [ ] **AC-7** Flutter 端扩展 S3-7 的 `CitationCard`，展示资源名称 + 页码/时间戳 + 片段，与答案中的 `[^n]` 标记联动
- [ ] **AC-8** 权限校验：引用仅包含用户已授权的 resource_id，未授权资源不进入引用列表（复用 S3-4 越权过滤结果）
- [ ] **AC-9** 单元/集成测试覆盖率 80%+，覆盖标记生成、映射、校验、音频/PDF 引用、SSE 事件与降级场景

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── services/
│   │   ├── citation_service.py        # 引用编排：格式化 + 校验
│   │   ├── citation_formatter.py      # [^n] 标记 -> chunk metadata 映射
│   │   └── citation_validator.py      # 幻觉引用剔除
│   ├── models/
│   │   ├── citation.py                # Citation 数据模型
│   │   └── citation_request.py
│   └── prompts/
│       └── rag_citation.txt           # 带引用指示的 Prompt 模板
├── config/
│   └── ai.yaml                        # citation 配置段
└── tests/
    ├── unit/test_citation_formatter.py
    ├── unit/test_citation_validator.py
    ├── unit/test_citation_service.py
    └── integration/test_citation_sse.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| pydantic | 2.x | Citation 模型校验 |
| Jinja2 | 3.1.x | 带引用指示的 Prompt 模板渲染 |
| zhipuai / openai | 2.x / 1.30+ | LLM 生成带 `[^n]` 标记的答案 |
| tiktoken | 0.7.x | snippet 片段 token 截断 |

---

## 技术要点

### 引用格式

答案中的引用标记采用 Markdown 脚注语法 `[^n]`，n 为 1 起递增整数，与上下文片段序号对齐。示例：

```text
本次会议主要讨论了产品路线图 [^1]，并确认了下个迭代的交付节点 [^2]。
```

### SSE 事件示例

复用 S3-6 SSE 问答链路，在 `done` 之前下发若干 `citation` 事件：

```text
event: chunk
data: {"message_id":"msg-1","delta":"本次会议主要讨论了产品路线图 [^1]"}

event: citation
data: {"message_id":"msg-1","chunk_id":"chunk-7","resource_id":"res-1","resource_type":"audio","timestamp_start":120.5,"timestamp_end":145.0,"score":0.89,"snippet":"产品路线图与下迭代交付节点..."}

event: citation
data: {"message_id":"msg-1","chunk_id":"chunk-3","resource_id":"res-2","resource_type":"pdf","page":3,"score":0.84,"snippet":"下个迭代的交付节点定于..."}

event: done
data: {"message_id":"msg-1","finish_reason":"stop"}
```

### 流程步骤

1. S3-4 检索返回 Top-K chunks，每个 chunk 携带 metadata（chunk_id、resource_id、page 或 timestamp_start/end、score）
2. Prompt 模板按序号注入上下文片段，并指示 LLM “在引用某片段时使用 `[^n]` 标记”
3. LLM 流式生成带 `[^n]` 标记的答案，chunk 事件逐字下发
4. 流式结束后，`CitationFormatter` 解析答案中的 `[^n]` 标记，按序号映射到对应 chunk metadata，生成 citations 列表
5. `CitationValidator` 校验每个标记的 chunk 存在且属于授权 resource，剔除无依据标记并记录日志
6. 按序下发 `citation` 事件，最后下发 `done`

### 错误处理与降级策略

- LLM 未插入任何 `[^n]` 标记：不下发 citation 事件，答案正常返回，日志记录“无引用”
- LLM 插入越序或重复标记（如 `[^3]` 但仅 2 个片段）：`CitationValidator` 剔除越序标记，保留有效引用
- chunk metadata 缺失 page/timestamp 字段：引用仅返回 resource_id 与 score，snippet 置空，不阻断流程
- 引用映射异常：降级为“无引用”模式，答案照常下发，记录 ERROR 日志
- 资源越权：引用列表中不包含未授权 resource_id（复用 S3-4 过滤结果）

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LLM 不稳定插入 `[^n]` 标记 | 引用缺失或编号错乱 | Prompt 强约束 + Validator 容错剔除，记录命中率指标 |
| chunk metadata 字段不统一 | 时间戳/页码引用失败 | 与 S3-1/S3-4 对齐 metadata schema，缺失字段降级处理 |
| 引用与答案语义不一致 | 用户被误导 | S4-6 跳转导航提供原文核对，后续引入引用相关性打分 |
| 大量引用导致 SSE 事件过多 | 客户端解析压力 | 限制单答案引用数上限（默认 8），超过则截断 |

---

## Web 端适配

- 引用事件由 S3-6 SSE 链路下发，Web 端 `EventSource` 复用现有解析逻辑，新增 `citation` 事件分支
- Flutter 端扩展 S3-7 的 `CitationCard`，按 `resource_type` 分别渲染：audio 显示 `mm:ss` 时间戳，pdf 显示“第 N 页”
- `CitationCard` 点击行为由 S4-6 实现跳转导航，本任务仅保证事件数据完整
- Web 端答案 Markdown 渲染需正确解析 `[^n]` 脚注并与 `CitationCard` 序号联动

---

## 备注

- 本任务复用 S3-6 SSE 问答接口，不新增对外端点，仅扩展响应中的 `citation` 事件
- `CitationService` 应设计为可注入 `RetrievalService`，便于 S4 Agent 工作流复用
- 引用命中率为关键质量指标，建议接入监控，便于后续 Prompt 调优
- 引用数据格式需与 S4-6 跳转导航契约对齐，避免字段二次转换
