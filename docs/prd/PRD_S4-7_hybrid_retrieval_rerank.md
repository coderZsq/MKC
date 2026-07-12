# PRD：[S4-7] 混合检索 + 重排序

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)、[PRD_S3-3_milvus_vector_store.md](./PRD_S3-3_milvus_vector_store.md)、[PRD_S3-1_text_chunking.md](./PRD_S3-1_text_chunking.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-7 |
| **任务名称** | 混合检索 + 重排序 |
| **所属史诗** | E6 知识库检索 |
| **故事点** | 5 |
| **优先级** | Should |
| **依赖** | S3-4 向量检索 + 上下文组装（[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)） |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为知识库问答链路的调用方（Gateway / S3-6 问答 API），我希望在 S3-4 纯向量检索之上叠加稀疏检索（BM25）与 Cross-Encoder 重排序，以便在术语精确命中、关键词匹配、专有名词等场景下提升 Top-K 的相关性，降低 LLM 答案幻觉，并为 S5 检索评估预留可对比的召回指标（纯向量 vs. 混合 + 重排）。本任务在 AI Service 中实现 BM25 稀疏检索、RRF 融合、Cross-Encoder 重排序与参数可配置化，作为 S3-4 `retrieve` 的增强路径。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供 `POST /ai/v1/retrieve/hybrid` 内部接口（`X-Internal-Key` 鉴权），输入问题与资源范围，返回重排后的 Top-K 文本块
- [ ] **AC-2** BM25 稀疏检索：使用 rank-bm25 对 chunk 文本建索引，中文经 jieba 分词，返回 Top-K 候选
- [ ] **AC-3** 向量稠密检索：复用 S3-3 Milvus + S3-2 text-embedding-v3，按 user_id / resource_ids 过滤，返回 Top-K 候选
- [ ] **AC-4** RRF 融合：以 Reciprocal Rank Fusion 合并两路 Top-K，`bm25_weight` / `vector_weight` / `rrf_k` 可配置
- [ ] **AC-5** Cross-Encoder 重排：使用 BAAI/bge-reranker-base 对融合后 Top-N 重排，取最终 Top-K
- [ ] **AC-6** 参数可配置：`bm25_weight`、`vector_weight`、`rerank_top_n`、`final_top_k`、`score_threshold` 均可通过 `config/ai.yaml` 配置并由请求参数覆盖
- [ ] **AC-7** 权限过滤：按 user_id 与 resource_ids 过滤，越权资源不可返回（BM25 与向量两路均强制过滤）
- [ ] **AC-8** 性能与降级：单次混合检索 + 重排端到端耗时 < 800ms（默认阈值），超时或重排失败时降级为纯向量检索
- [ ] **AC-9** 中文分词：jieba 对 query 与 chunk 文本分词，BM25 在分词后语料上构建，支持中英文混合
- [ ] **AC-10** 单元/集成测试覆盖率 80%+，使用 mock BM25 / 向量库 / Reranker 验证融合与重排逻辑

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── api/
│   │   └── hybrid_retrieval.py            # 混合检索接口
│   ├── services/
│   │   ├── hybrid_retrieval_service.py    # 混合检索编排：BM25 + 向量 + RRF + 重排
│   │   ├── bm25_store.py                  # BM25 稀疏检索（rank-bm25 + jieba）
│   │   └── reranker.py                    # Cross-Encoder 重排（bge-reranker-base）
│   └── models/
│       ├── hybrid_retrieval_request.py
│       └── hybrid_retrieval_result.py
├── config/
│   └── ai.yaml
└── tests/
    ├── unit/test_bm25_store.py
    ├── unit/test_reranker.py
    ├── unit/test_rrf_fusion.py
    ├── unit/test_hybrid_retrieval_service.py
    └── integration/test_hybrid_retrieval_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| rank-bm25 | 0.2.x | BM25 稀疏检索 |
| jieba | 0.42.x | 中文分词 |
| sentence-transformers | 2.x | 加载 Cross-Encoder（BAAI/bge-reranker-base） |
| numpy | 1.26.x | RRF 融合分数计算 |
| pydantic | 2.x | 请求/响应模型校验 |
| pymilvus | 2.4.x | 稠密向量检索（S3-3 复用） |

---

## 技术要点

### 请求/响应示例

**请求**

```json
POST /ai/v1/retrieve/hybrid
Headers: X-Internal-Key: <key>
{
  "question": "本次会议的议题是什么？",
  "user_id": "user-1",
  "resource_ids": ["res-1"],
  "bm25_weight": 1.0,
  "vector_weight": 1.0,
  "rerank_top_n": 20,
  "final_top_k": 5,
  "score_threshold": 0.0
}
```

**响应**

```json
{
  "chunks": [
    {
      "chunk_id": "chunk-1",
      "resource_id": "res-1",
      "text": "本次会议主要讨论了...",
      "score": 0.92,
      "source": "rerank",
      "metadata": {"page": 3}
    }
  ],
  "fusion": {"bm25_count": 5, "vector_count": 5, "fused_count": 8},
  "elapsed_ms": 620
}
```

### 融合 / 重排流程

1. 校验 `X-Internal-Key` 与请求参数（question 非空、resource_ids 非空）
2. 校验用户资源权限（resource_ids 归属 user_id）
3. **BM25 稀疏检索**：按 resource_ids 从存储加载 chunk 文本，jieba 分词后构建 BM25 索引，对分词后的 query 检索 Top-K
4. **向量稠密检索**：调用 `EmbeddingService.embed_query()` 生成 query vector，在 Milvus 中按 user_id + resource_ids 过滤检索 Top-K
5. **RRF 融合**：以 `score = w_bm25 / (k + rank_bm25) + w_vector / (k + rank_vector)` 合并两路结果，按融合分排序取 Top-N（`rerank_top_n`）
6. **Cross-Encoder 重排**：以 `(question, chunk.text)` 对输入 bge-reranker-base，按输出 logits 降序取 Top-K（`final_top_k`）
7. 过滤低于 `score_threshold` 的块，组装元数据（chunk_id、resource_id、text、score、source、metadata）
8. 返回结果与融合统计（bm25_count / vector_count / fused_count / elapsed_ms）

### 错误处理与降级策略

- **检索无结果**：返回空 chunks，`fusion` 计数为 0，不触发重排
- **BM25 失败**：记录告警，仅使用向量检索结果进入重排（降级路径 1）
- **向量检索失败**：记录告警，仅使用 BM25 结果进入重排（降级路径 2）
- **重排失败或超时**：跳过重排，直接返回 RRF 融合后 Top-K（降级路径 3）
- **整体超时（> timeout_ms）**：降级为纯向量检索（S3-4 `retrieve`），响应中标记 `degraded: true`
- **资源越权**：返回 403，不暴露任何数据
- **模型加载失败**：启动时校验 reranker 模型可用性，不可用时禁用重排并告警

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| bge-reranker-base 模型体积大、加载慢 | 首次请求延迟高 | 启动时预加载模型，运行时复用实例 |
| BM25 大语料构建耗时 | 单次检索超阈值 | 按 resource_ids 限定语料范围，进程内缓存索引 |
| jieba 分词与术语不匹配 | 召回率下降 | 支持自定义词典加载，后续 Sprint 优化 |
| 重排 GPU 不可用 | CPU 推理慢 | 默认 CPU 部署，限制 `rerank_top_n` 控制成本 |
| 两路检索结果 ID 不一致 | RRF 合并困难 | 以 chunk_id 为主键去重合并 |

---

## Web 端适配

混合检索接口为 AI Service 内部接口（`X-Internal-Key`），由 Gateway 在问答链路中调用。Web 端不直接访问，仅通过 S3-6 问答 SSE 间接消费。Gateway 侧可按配置选择调用 `/ai/v1/retrieve`（纯向量）或 `/ai/v1/retrieve/hybrid`（混合 + 重排），前端无需感知差异。

---

## 备注

- 本任务为 S3-4 检索能力的增强，不破坏 S3-4 接口契约；`/ai/v1/retrieve/hybrid` 与 `/ai/v1/retrieve` 并存
- BM25 索引为进程内内存索引，按 resource_ids 范围构建；生产环境可后续替换为 Elasticsearch（接口保持一致）
- 评估指标（召回率、MRR、nDCG）为 S5 评估任务预留，本任务在响应中返回 `elapsed_ms` 与融合统计便于对比
- `bm25_weight` / `vector_weight` 建议做成运行时参数，便于 A/B 测试与调参
- Reranker 模型实例应设计为单例可注入，便于测试替换为 mock
