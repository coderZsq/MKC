# PRD：[S3-1] 文本分块策略实现

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S2-3_audio_text_cleaning.md](./PRD_S2-3_audio_text_cleaning.md)、[PRD_S2-4_pdf_text_extraction.md](./PRD_S2-4_pdf_text_extraction.md)、[PRD_S3-2_text_embedding_v3.md](./PRD_S3-2_text_embedding_v3.md)、[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-1 |
| **任务名称** | 文本分块策略实现 |
| **所属史诗** | E6 知识库检索 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S2-3 音频文本清洗、S2-4 PDF 文本提取 |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为用户，我希望系统对音频转录文本和 PDF 解析文本进行合理分块，以便后续 Embedding 和检索时能够召回语义完整、粒度适中的内容片段。本任务在 AI Service 中实现可配置、可扩展的文本分块策略，并保证分块后保留来源元数据（资源 ID、页码、时间戳等）。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供 `ChunkingService` 统一接口，支持至少三种策略：按段落、按固定 token 长度、按语义边界（章节标题/空行）
- [ ] **AC-2** 每个分块保留原始元数据：资源 ID、块序号、起始位置、结束位置、页码或时间戳范围
- [ ] **AC-3** 支持相邻块之间的重叠窗口，重叠 token 数可配置（默认 50 tokens）
- [ ] **AC-4** 单个块默认最大 token 数不超过 512，避免 Embedding 模型截断
- [ ] **AC-5** 中文按字/词混合估算，英文按 token 估算，混合文本也能合理分块
- [ ] **AC-6** 空块、超长段、跨章节边界等边界场景得到合理处理
- [ ] **AC-7** 分块策略通过 `config/ai.yaml` 配置化，无需修改代码即可切换策略和参数
- [ ] **AC-8** 单元测试覆盖率 80%+，覆盖所有策略与边界场景

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── services/
│   │   ├── chunking/
│   │   │   ├── __init__.py
│   │   │   ├── chunking_service.py      # 统一入口
│   │   │   ├── base_chunker.py          # 抽象基类
│   │   │   ├── paragraph_chunker.py     # 段落分块
│   │   │   ├── fixed_token_chunker.py   # 固定 token 分块
│   │   │   └── semantic_chunker.py      # 语义边界分块
│   │   └── models/
│   │       └── chunk.py                 # Chunk 数据模型
├── config/
│   └── ai.yaml                          # chunking 配置段
└── tests/
    ├── unit/test_chunking_service.py
    ├── unit/test_paragraph_chunker.py
    ├── unit/test_fixed_token_chunker.py
    └── unit/test_semantic_chunker.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| tiktoken | 0.7.x | OpenAI 兼容 tokenizer，用于 token 估算 |
| langchain-text-splitters | 0.0.x | 备选分块实现参考 |
| pydantic | 2.x | Chunk 模型校验 |
| PyYAML | 6.x | 配置加载 |

---

## 技术要点

### 配置示例

```yaml
chunking:
  strategy: paragraph            # paragraph / fixed_token / semantic
  chunk_size: 512                # 最大 token 数
  chunk_overlap: 50              # 重叠 token 数
  separators: ["\n## ", "\n# ", "\n\n", "\n", "。", "，", " ", ""]
  preserve_metadata: true
```

### Chunk 数据模型

```python
class Chunk(BaseModel):
    id: str
    resource_id: str
    index: int
    text: str
    start_pos: int
    end_pos: int
    metadata: dict = {}           # page, timestamp_start, timestamp_end, etc.
    token_count: int
```

### 分块策略说明

- **段落分块**：以空行为边界，适用于清洗后的口语转录文本，保持语义完整
- **固定 token 分块**：按 chunk_size 切分，超长段落会被拆散，适合结构不规整的文本
- **语义边界分块**：优先按 Markdown 标题、`#` 标题、章节号切分，适合 PDF 结构化文本

### 错误处理与降级策略

- 空文本输入：返回空列表，不抛异常
- 超长无分隔符文本：强制按字符截断并打印警告日志
- 配置缺失 strategy：使用默认 `paragraph` 策略
- tokenizer 加载失败：使用基于字符数的近似估算作为降级

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 中文分词与 token 估算不一致 | 块长度超出 Embedding 模型限制 | 同时使用字数和 token 双重估算，取较小值 |
| 章节标题识别规则不准确 | 分块语义边界混乱 | 先实现简单规则，S4 引入 LLM 语义切分 |
| 元数据丢失导致后续溯源困难 | 引用跳转不准 | 分块时强制校验必填元数据字段 |

---

## Web 端适配

本任务为后端 AI Service 能力，Web 端不直接调用。分块结果由 S3-2 Embedding 与 S3-4 检索使用，最终影响 Web 端答案质量与引用来源。

---

## 备注

- S3-1 先保证基础分块策略，S4 可引入更智能的语义分块（如 LLM 辅助段落聚合）
- 分块元数据格式需要与 S3-3 Milvus 集合 schema 对齐，避免字段不一致
- 分块结果应可被重新生成（资源重新处理时清空旧块）
