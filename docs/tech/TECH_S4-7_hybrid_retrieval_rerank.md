# 技术文档：[S4-7] 混合检索 + 重排序

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S4-7_hybrid_retrieval_rerank.md](../prd/PRD_S4-7_hybrid_retrieval_rerank.md)

---

## 1. 文档目标

定义 AI Service 中混合检索与重排序模块的技术实现：BM25 稀疏检索、向量稠密检索复用、RRF 融合、Cross-Encoder 重排、参数配置、降级策略与测试方案。本任务增强 S3-4 的纯向量检索路径，提供 `/ai/v1/retrieve/hybrid` 内部接口。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- pydantic 2.x
- numpy 1.26.x
- rank-bm25 0.2.x（BM25 稀疏检索）
- jieba 0.42.x（中文分词）
- sentence-transformers 2.x（加载 Cross-Encoder）
- BAAI/bge-reranker-base（重排模型）
- pymilvus 2.4.x（稠密向量检索，复用 S3-3）

> 稀疏检索选型说明：本任务采用 rank-bm25 + jieba 方案，进程内内存索引，零外部依赖、便于本地与 CI 运行。生产环境若需大规模语料或持久化，可替换为 Elasticsearch 实现（保持 `BM25Store` 抽象接口不变）。

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/retrieve/hybrid` | Internal API Key（`X-Internal-Key`） | BM25 + 向量 + RRF 融合 + Cross-Encoder 重排 |

### 请求示例

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

### 响应示例

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
  "degraded": false,
  "elapsed_ms": 620
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | INVALID_REQUEST | 缺少 question 或 resource_ids |
| 401 | UNAUTHORIZED | 缺少或无效 X-Internal-Key |
| 403 | FORBIDDEN | 无权访问资源 |
| 503 | RETRIEVAL_UNAVAILABLE | 检索服务不可用（两路均失败且无法降级） |

---

## 4. 配置

新增 `config/ai.yaml` 中 `hybrid_retrieval` 段：

```yaml
hybrid_retrieval:
  bm25_weight: 1.0
  vector_weight: 1.0
  rrf_k: 60
  rerank_top_n: 20
  final_top_k: 5
  score_threshold: 0.0
  timeout_ms: 800
  fallback_to_vector: true
  bm25:
    tokenizer: jieba
    user_dict: ""               # 可选自定义词典路径
    cache_index: true           # 进程内缓存 BM25 索引
  reranker:
    model_name: "BAAI/bge-reranker-base"
    device: "cpu"
    max_length: 512
    enabled: true
```

---

## 5. 模块设计

### 5.1 HybridRetrievalService

```python
class HybridRetrievalService:
    def __init__(
        self,
        bm25_store: "BM25Store",
        embedding_svc,
        vector_store,
        reranker: "Reranker",
        config: HybridRetrievalConfig,
    ) -> None:
        self._bm25 = bm25_store
        self._embedding_svc = embedding_svc
        self._vector_store = vector_store
        self._reranker = reranker
        self._config = config

    async def retrieve(self, request: HybridRetrievalRequest) -> HybridRetrievalResult:
        ...
```

### 5.2 BM25Store

```python
class BM25Store:
    def __init__(self, tokenizer: str = "jieba", user_dict: str = "") -> None:
        ...

    def index(self, docs: list[SearchResult]) -> None:
        """对给定 chunk 文本构建 BM25 索引（分词后）。"""

    def search(
        self,
        query: str,
        top_k: int,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """分词后检索 Top-K，按 filters 过滤 user_id / resource_ids。"""
```

### 5.3 Reranker

```python
class Reranker:
    def __init__(self, model_name: str, device: str = "cpu", enabled: bool = True) -> None:
        ...

    def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
    ) -> list[SearchResult]:
        """Cross-Encoder 对 (query, text) 打分，返回 Top-N。"""
```

---

## 6. 关键代码实现

### 6.1 RRF 融合

```python
def reciprocal_rank_fusion(
    bm25_hits: list[SearchResult],
    vector_hits: list[SearchResult],
    bm25_weight: float = 1.0,
    vector_weight: float = 1.0,
    k: int = 60,
) -> list[SearchResult]:
    """Reciprocal Rank Fusion：以 chunk_id 去重合并两路结果。

    score = w_bm25 / (k + rank_bm25) + w_vector / (k + rank_vector)
    """
    scores: dict[str, float] = {}
    meta: dict[str, SearchResult] = {}

    for rank, hit in enumerate(bm25_hits):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + bm25_weight / (k + rank + 1)
        meta.setdefault(hit.chunk_id, hit)

    for rank, hit in enumerate(vector_hits):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + vector_weight / (k + rank + 1)
        meta.setdefault(hit.chunk_id, hit)

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [meta[cid].model_copy(update={"score": float(s)}) for cid, s in ordered]
```

### 6.2 Cross-Encoder 重排

```python
from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self, model_name: str, device: str = "cpu", enabled: bool = True) -> None:
        self._enabled = enabled
        self._model = (
            CrossEncoder(model_name, device=device) if enabled else None
        )

    def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
    ) -> list[SearchResult]:
        if not candidates or not self._enabled or self._model is None:
            return candidates[:top_n]

        pairs = [(query, c.text) for c in candidates]
        raw_scores = self._model.predict(pairs)
        ranked = sorted(
            zip(candidates, raw_scores),
            key=lambda item: item[1],
            reverse=True,
        )[:top_n]
        return [
            c.model_copy(update={"score": float(s), "source": "rerank"})
            for c, s in ranked
        ]
```

### 6.3 BM25Store（rank-bm25 + jieba）

```python
import jieba
from rank_bm25 import BM25Okapi


class BM25Store:
    def __init__(self, tokenizer: str = "jieba", user_dict: str = "") -> None:
        if user_dict:
            jieba.load_userdict(user_dict)
        self._docs: list[SearchResult] = []
        self._bm25: BM25Okapi | None = None

    def index(self, docs: list[SearchResult]) -> None:
        self._docs = list(docs)
        tokenized = [list(jieba.cut(d.text)) for d in self._docs]
        self._bm25 = BM25Okapi(tokenized)

    def search(
        self,
        query: str,
        top_k: int,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        if self._bm25 is None:
            return []
        tokens = list(jieba.cut(query))
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        results: list[SearchResult] = []
        for idx, score in ranked:
            if score <= 0:
                continue
            doc = self._docs[idx]
            if not self._matches_filters(doc, filters):
                continue
            results.append(doc.model_copy(update={"score": float(score), "source": "bm25"}))
        return results

    @staticmethod
    def _matches_filters(doc: SearchResult, filters: dict | None) -> bool:
        if not filters:
            return True
        resource_ids = filters.get("resource_ids")
        if resource_ids and doc.resource_id not in resource_ids:
            return False
        user_id = filters.get("user_id")
        if user_id and doc.user_id != user_id:
            return False
        return True
```

### 6.4 HybridRetrievalService 编排（含降级）

```python
async def retrieve(self, request: HybridRetrievalRequest) -> HybridRetrievalResult:
    filters = {"user_id": request.user_id, "resource_ids": request.resource_ids}
    bm25_hits: list[SearchResult] = []
    vector_hits: list[SearchResult] = []
    degraded = False

    try:
        docs = await self._load_chunks(request.resource_ids, request.user_id)
        self._bm25.index(docs)
        bm25_hits = self._bm25.search(request.question, request.rerank_top_n, filters)
    except Exception:
        degraded = True

    try:
        query_vector = await self._embedding_svc.embed_query(request.question)
        vector_hits = await self._vector_store.search(
            query_vector, request.rerank_top_n, filters=filters
        )
    except Exception:
        degraded = True

    if not bm25_hits and not vector_hits:
        return HybridRetrievalResult(chunks=[], fusion=..., degraded=degraded)

    fused = reciprocal_rank_fusion(
        bm25_hits, vector_hits,
        bm25_weight=request.bm25_weight,
        vector_weight=request.vector_weight,
        k=self._config.rrf_k,
    )[: request.rerank_top_n]

    try:
        reranked = self._reranker.rerank(request.question, fused, request.final_top_k)
    except Exception:
        degraded = True
        reranked = fused[: request.final_top_k]

    filtered = [c for c in reranked if c.score >= request.score_threshold]
    return HybridRetrievalResult(chunks=filtered, fusion=..., degraded=degraded)
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 缺少 question 或 resource_ids | 400 | INVALID_REQUEST | 缺少问题或资源范围 |
| 缺少/无效 X-Internal-Key | 401 | UNAUTHORIZED | 无效内部密钥 |
| 资源越权 | 403 | FORBIDDEN | 无权访问资源 |
| BM25 失败 | 200 | - | 降级仅用向量，`degraded=true` |
| 向量检索失败 | 200 | - | 降级仅用 BM25，`degraded=true` |
| 重排失败/超时 | 200 | - | 降级返回 RRF 结果，`degraded=true` |
| 两路均失败且无法降级 | 503 | RETRIEVAL_UNAVAILABLE | 检索不可用 |
| 无检索结果 | 200 | - | 返回空 chunks |

---

## 8. Web 端适配要点

- `/ai/v1/retrieve/hybrid` 为内部接口，仅 Gateway 通过 `X-Internal-Key` 调用
- Gateway 可按配置选择 `/ai/v1/retrieve`（纯向量）或 `/ai/v1/retrieve/hybrid`（混合 + 重排）
- Web 端通过 S3-6 问答 SSE 间接消费，前端无需感知检索模式
- 响应中 `degraded` 字段可供 Gateway 记录降级事件，不影响前端展示

---

## 9. 测试策略

- **单元测试**：RRF 融合（去重、权重、排序）、BM25Store（分词、过滤、Top-K）、Reranker（mock 模型分数、top_n 截断）、降级分支
- **集成测试**：mock EmbeddingService / VectorStore / Reranker，验证 `HybridRetrievalService.retrieve` 端到端编排
- **Mock 策略**：固定 query 向量、固定 BM25 返回、Reranker 返回预设分数序列
- **性能测试**：mock 依赖下端到端耗时 < 800ms，超时触发降级
- **评估预留**：响应返回 `elapsed_ms` 与 `fusion` 统计，供 S5 对比纯向量 vs. 混合召回率

---

## 10. 检查清单

- [ ] `HybridRetrievalService` 编排：BM25 + 向量 + RRF + 重排
- [ ] `BM25Store` rank-bm25 + jieba 中文分词
- [ ] `Reranker` Cross-Encoder（bge-reranker-base）重排
- [ ] RRF 融合以 chunk_id 去重，权重可配置
- [ ] 参数 bm25_weight / vector_weight / rerank_top_n / final_top_k 可配置
- [ ] 权限过滤（user_id / resource_ids）两路均强制
- [ ] 降级策略：BM25/向量/重排单点失败不阻塞
- [ ] 超时降级为纯向量检索
- [ ] 来源元数据保留（chunk_id、resource_id、score、source、metadata）
- [ ] 测试覆盖率 80%+
- [ ] ruff / mypy 通过
- [ ] 无硬编码密钥（API key 仅 env var）
- [ ] OpenAPI / 文档同步更新
