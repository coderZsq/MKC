# S4-7 测试用例：混合检索 + 重排序

## 1. 范围与目标

验证 AI Service 混合检索与重排序模块：BM25 稀疏检索（rank-bm25 + jieba）、向量稠密检索复用、RRF 融合、Cross-Encoder 重排、参数可配置、权限过滤、降级策略、性能与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- rank-bm25 0.2.x、jieba 0.42.x
- sentence-transformers 2.x（BAAI/bge-reranker-base）
- numpy 1.26.x、pydantic 2.x
- pytest、pytest-cov、ruff、mypy
- mock EmbeddingService / VectorStore / Reranker

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-7-001 | Functional | Integration | P0 | 混合检索接口返回重排 Top-K | 已索引数据 | POST /ai/v1/retrieve/hybrid | 返回 chunks、fusion 统计、elapsed_ms | PRD AC-1 |
| MKC-TC-S4-7-002 | Functional | Unit | P0 | BM25 稀疏检索返回 Top-K | BM25Store 已建索引 | 调用 bm25_store.search | 返回按 BM25 分排序的 Top-K，source=bm25 | PRD AC-2 |
| MKC-TC-S4-7-003 | Functional | Unit | P0 | 向量稠密检索复用 S3-3 | mock VectorStore | 调用 retrieve | 调用 embed_query + vector_store.search 并返回 Top-K | PRD AC-3 |
| MKC-TC-S4-7-004 | Functional | Unit | P0 | RRF 融合合并两路结果 | 提供 bm25_hits 与 vector_hits | 调用 reciprocal_rank_fusion | 以 chunk_id 去重，按融合分排序 | PRD AC-4 |
| MKC-TC-S4-7-005 | Functional | Unit | P0 | Cross-Encoder 重排取 Top-K | mock Reranker 返回分数 | 调用 reranker.rerank | 按分数降序取 final_top_k，source=rerank | PRD AC-5 |
| MKC-TC-S4-7-006 | Functional | Unit | P1 | 参数可通过请求覆盖配置 | 配置默认值 | 请求传入 bm25_weight/vector_weight/rerank_top_n/final_top_k | 使用请求参数而非默认值 | PRD AC-6 |
| MKC-TC-S4-7-007 | Functional | Unit | P1 | RRF 权重影响融合排序 | 同一候选集 | 设置 bm25_weight=2, vector_weight=1 | BM25 命中项排名上升 | PRD AC-4 |
| MKC-TC-S4-7-008 | Functional | Unit | P1 | 重排后结果按分数降序 | 候选含乱序分数 | 调用 reranker.rerank | 返回结果分数降序 | PRD AC-5 |
| MKC-TC-S4-7-009 | Functional | Unit | P2 | 融合后截取 rerank_top_n | 融合结果 > rerank_top_n | 调用 retrieve | 进入重排的候选数 = rerank_top_n | PRD AC-6 |
| MKC-TC-S4-7-010 | Functional | Unit | P2 | score_threshold 过滤低分块 | 配置 threshold | 调用 retrieve | 低于阈值的块被过滤 | PRD AC-6 |
| MKC-TC-S4-7-011 | Functional | Unit | P1 | jieba 中文分词后建索引 | 中文 chunk 文本 | 调用 bm25_store.index + search | 分词后命中中文关键词 | PRD AC-9 |
| MKC-TC-S4-7-012 | Functional | Unit | P2 | 中英文混合 query 检索 | 中英文混合 chunk | 调用 bm25_store.search | 中英文 token 均参与打分 | PRD AC-9 |
| MKC-TC-S4-7-013 | Functional | Unit | P2 | 返回块含来源元数据 | 数据带 metadata | 调用 retrieve | 返回 chunk_id/resource_id/score/source/metadata | PRD AC-1 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-7-014 | Security | Integration | P0 | 缺少 X-Internal-Key 拒绝访问 | 请求头无 Key | POST /ai/v1/retrieve/hybrid | 返回 401 UNAUTHORIZED | TECH 3 |
| MKC-TC-S4-7-015 | Security | Unit | P0 | 按 user_id 过滤 BM25 结果 | 含他人资源 | 调用 bm25_store.search | 仅返回归属 user 的块 | PRD AC-7 |
| MKC-TC-S4-7-016 | Security | Unit | P0 | 按 resource_ids 过滤两路检索 | 含未授权 resource | 调用 retrieve | BM25 与向量均过滤 resource_ids | PRD AC-7 |
| MKC-TC-S4-7-017 | Security | Integration | P0 | 越权 resource_id 返回 403 | 传入他人 resource_id | POST /ai/v1/retrieve/hybrid | 返回 403 FORBIDDEN | PRD AC-7 |
| MKC-TC-S4-7-018 | Security | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 API key | 仅 .env / env var 出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-7-019 | Negative | Integration | P0 | 缺少 question 返回 400 | 请求无 question | POST /ai/v1/retrieve/hybrid | 返回 INVALID_REQUEST | PRD AC-1 |
| MKC-TC-S4-7-020 | Negative | Integration | P0 | 缺少 resource_ids 返回 400 | 请求无 resource_ids | POST /ai/v1/retrieve/hybrid | 返回 INVALID_REQUEST | PRD AC-1 |
| MKC-TC-S4-7-021 | Negative | Unit | P1 | 检索无结果返回空 chunks | 无相关数据 | 调用 retrieve | chunks 为空，fusion 计数为 0 | PRD 降级策略 |
| MKC-TC-S4-7-022 | Reliability | Unit | P1 | BM25 失败降级仅用向量 | mock bm25_store 异常 | 调用 retrieve | 返回向量结果，degraded=true | PRD AC-8 |
| MKC-TC-S4-7-023 | Reliability | Unit | P1 | 向量检索失败降级仅用 BM25 | mock vector_store 异常 | 调用 retrieve | 返回 BM25 结果，degraded=true | PRD AC-8 |
| MKC-TC-S4-7-024 | Reliability | Unit | P1 | 重排失败降级返回 RRF 结果 | mock reranker 异常 | 调用 retrieve | 返回 RRF 融合 Top-K，degraded=true | PRD AC-8 |
| MKC-TC-S4-7-025 | Reliability | Unit | P1 | 整体超时降级为纯向量 | mock 耗时 > timeout_ms | 调用 retrieve | 降级调用 S3-4 纯向量，degraded=true | PRD AC-8 |
| MKC-TC-S4-7-026 | Negative | Unit | P2 | 两路均失败返回 503 | mock 两路均异常且 fallback 关闭 | 调用 retrieve | 返回 RETRIEVAL_UNAVAILABLE | PRD 降级策略 |
| MKC-TC-S4-7-027 | Negative | Unit | P2 | reranker 禁用时跳过重排 | config reranker.enabled=false | 调用 retrieve | 直接返回 RRF 融合 Top-K | PRD AC-8 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-7-028 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-10 |
| MKC-TC-S4-7-029 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行 ruff + mypy | 0 issues | 工程规范 |
| MKC-TC-S4-7-030 | Security | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 | 仅 .env / env var 出现 | 安全基线 |
| MKC-TC-S4-7-031 | Functional | Static | P2 | 不可变模式校验 | 代码存在 | 审查 model_copy 使用 | 无原地修改 SearchResult | 工程规范 |

### 3.5 兼容性与性能

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-7-032 | Performance | Unit | P1 | 端到端耗时 < 800ms | mock 依赖 | 调用 retrieve | elapsed_ms < 800 | PRD AC-8 |
| MKC-TC-S4-7-033 | Performance | Unit | P2 | reranker 仅对 top_n 候选打分 | 融合结果 > rerank_top_n | 调用 reranker.rerank | predict 输入数 = rerank_top_n | PRD AC-8 |
| MKC-TC-S4-7-034 | Compatibility | Unit | P2 | 与 S3-4 retrieve 接口并存 | 两接口均存在 | 分别调用 /retrieve 与 /retrieve/hybrid | 互不影响，各自返回 | PRD 备注 |
| MKC-TC-S4-7-035 | Compatibility | Integration | P2 | Gateway 切换检索模式 | 配置两种模式 | Gateway 调用混合接口 | 正常返回 chunks | PRD Web 端适配 |
| MKC-TC-S4-7-036 | Performance | Unit | P2 | BM25 索引缓存命中 | 同 resource_ids 二次查询 | 调用 retrieve | 复用缓存索引，耗时下降 | PRD 阻塞风险 |

## 4. 测试执行清单

- [ ] 混合检索接口端到端
- [ ] BM25 稀疏检索 + jieba 中文分词
- [ ] 向量稠密检索复用 S3-3
- [ ] RRF 融合（去重、权重、排序）
- [ ] Cross-Encoder 重排（top_n 截断、source 标记）
- [ ] 参数可配置（请求覆盖配置）
- [ ] 权限过滤（user_id / resource_ids 两路）
- [ ] 越权返回 403
- [ ] 缺少 question / resource_ids 返回 400
- [ ] 降级策略（BM25/向量/重排/超时）
- [ ] 性能 < 800ms
- [ ] 覆盖率 80%+
- [ ] ruff / mypy 通过
- [ ] 无硬编码密钥
- [ ] 不可变模式校验

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
