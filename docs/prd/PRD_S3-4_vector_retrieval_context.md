# PRD：[S3-4] 实现向量检索 + 上下文组装

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S3-1_text_chunking.md](./PRD_S3-1_text_chunking.md)、[PRD_S3-2_text_embedding_v3.md](./PRD_S3-2_text_embedding_v3.md)、[PRD_S3-3_milvus_vector_store.md](./PRD_S3-3_milvus_vector_store.md)、[PRD_S3-5_glm4_kimi_llm.md](./PRD_S3-5_glm4_kimi_llm.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-4 |
| **任务名称** | 实现向量检索 + 上下文组装 |
| **所属史诗** | E6 知识库检索 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S3-1 文本分块、S3-3 Milvus 向量存储 |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为用户，当我向知识库提问时，我希望系统能够召回与问题最相关的文本片段，并将这些片段组装成结构化的上下文，供 LLM 生成基于文档内容的答案。本任务在 AI Service 中实现向量检索、相关性过滤、上下文压缩与 Prompt 构建，为 S3-5 的 LLM 生成提供高质量输入。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供 `POST /ai/v1/retrieve` 接口，输入问题与资源范围，返回 Top-K 相关文本块
- [ ] **AC-2** 先对问题生成 Embedding，再在 Milvus 中执行相似度检索，默认 Top-K=5
- [ ] **AC-3** 支持按 user_id 和 resource_id 列表过滤，未授权资源不可返回
- [ ] **AC-4** 支持相似度阈值过滤，低于阈值的块不进入上下文
- [ ] **AC-5** 上下文组装按相关性排序，并控制总 token 数不超过 LLM 上下文窗口（默认 4k tokens）
- [ ] **AC-6** 每个返回块包含来源元数据：资源 ID、页码或时间戳、相似度分数
- [ ] **AC-7** 提供标准化 Prompt 模板，将上下文与问题组合为 LLM 输入
- [ ] **AC-8** 单元/集成测试覆盖率 80%+，使用 mock 向量库验证检索与组装逻辑

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── api/
│   │   └── retrieval.py              # 检索接口
│   ├── services/
│   │   ├── retrieval_service.py      # 检索编排
│   │   ├── prompt_builder.py         # Prompt 构建
│   │   └── ranking_service.py        # 简单重排序（可选）
│   └── models/
│       ├── retrieval_request.py
│       ├── retrieval_result.py
│       └── prompt_context.py
├── config/
│   └── ai.yaml
└── tests/
    ├── unit/test_retrieval_service.py
    ├── unit/test_prompt_builder.py
    └── integration/test_retrieval_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Jinja2 | 3.1.x | Prompt 模板渲染 |
| tiktoken | 0.7.x | 上下文 token 估算 |
| numpy | 1.26.x | 相似度计算 |
| pydantic | 2.x | 模型校验 |

---

## 技术要点

### 请求/响应示例

**请求**

```json
{
  "question": "本次会议的议题是什么？",
  "resource_ids": ["01922b9c-..."],
  "top_k": 5,
  "score_threshold": 0.7
}
```

**响应**

```json
{
  "chunks": [
    {
      "chunk_id": "...",
      "resource_id": "...",
      "text": "本次会议主要讨论了...",
      "score": 0.89,
      "metadata": {"page": 3, "timestamp_start": 120.0}
    }
  ],
  "prompt": "基于以下上下文..."
}
```

### 检索流程

1. 校验用户资源权限（resource_ids 归属 user）
2. 对问题调用 `EmbeddingService.embed()` 生成 query vector
3. 在 `VectorStore.search()` 中按 user_id + resource_ids 过滤
4. 对结果按 score 排序，过滤低于阈值
5. 按 token 预算选取前 N 个 chunk
6. 使用 Jinja2 模板构建 Prompt

### Prompt 模板示例

```jinja2
你是知识库助手。请基于以下上下文回答用户问题。
上下文：
{% for chunk in chunks %}
[{{ loop.index }}] {{ chunk.text }} （来源：{{ chunk.metadata }}）
{% endfor %}

用户问题：{{ question }}
请给出简洁、准确的回答。
```

### 错误处理与降级策略

- 检索无结果：返回空上下文，Prompt 中提示“无相关知识”
- 向量库不可用：返回 503，由 Gateway 提示用户稍后重试
- 上下文超出 token 限制：按相关性截断，保留高分块
- 资源越权：返回 403，不暴露任何数据

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 检索结果与问题相关性差 | 答案质量低 | 调整 top_k、score_threshold，S4 引入混合检索 |
| 上下文 token 超限 | LLM 截断 | 动态预算控制，优先保留高分块 |
| 元数据字段不统一 | 引用溯源失败 | 与 S3-1 协商统一 metadata schema |

---

## Web 端适配

检索接口为 AI Service 内部接口，由 Gateway 在问答链路中调用。Web 端不直接访问，仅通过 S3-6 问答 API 和 S3-7 对话页面间接使用。

---

## 备注

- S3-4 的上下文组装是 S3-5 LLM 生成的前置步骤，需明确接口边界
- 建议将 `PromptBuilder` 设计为可注入模板，便于 S4 Agent 工作流扩展
- 相似度阈值和 top_k 建议做成运行时参数，便于 A/B 测试
