# 技术文档：[S6-5] 实现 LlamaIndex Retriever/QueryEngine 封装

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-5_llamaindex_retriever_query_engine.md](../prd/PRD_S6-5_llamaindex_retriever_query_engine.md)

---

## 1. 文档目标

定义 LlamaIndex retrieval engine 的输入输出、上下文压缩、权限校验、空结果降级和 prompt 构建方式。

---

## 2. 技术栈

- Python 3.11+
- llama-index-core
- pydantic 2.x
- Milvus adapter
- pytest

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 内部 | `LlamaIndexRetrievalEngine.retrieve` | 无 | `RetrievalRequest -> RetrievalResult` |

---

## 4. 配置

```yaml
rag:
  llamaindex:
    default_top_k: 5
    score_threshold: 0.7
    max_context_tokens: 4096
    per_resource_candidates: true
```

---

## 5. 模块设计

- `retrieval_engine.py`：实现统一 retrieve 契约。
- `context_compressor.py`：复用 `TokenEstimator` 控制上下文长度。
- `query_engine.py`：可选封装 LlamaIndex retriever，不直接生成答案。
- `PromptBuilder`：继续复用 legacy prompt 构建，降低行为差异。

---

## 6. 关键代码实现

```python
class LlamaIndexRetrievalEngine:
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        nodes = self._retriever.retrieve(request.question)
        chunks = [node_with_score_to_chunk(node) for node in nodes]
        chunks = self._filter_and_authorize(chunks, request)
        chunks, token_count = self._compress(chunks, request.max_context_tokens)
        return RetrievalResult(
            chunks=chunks,
            prompt=self._prompt_builder.build(chunks, request.question),
            context_token_count=token_count,
        )
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 检索后越权结果 | 403 | RETRIEVAL_FORBIDDEN | 无权访问资源 |
| LlamaIndex 检索异常 | 503 | RETRIEVAL_UNAVAILABLE | 检索不可用 |
| 参数不合法 | 400 | INVALID_RETRIEVAL_REQUEST | 检索请求不合法 |

---

## 8. Web 端适配要点

无需 Web 端改动。输出 citation metadata 必须兼容现有 Flutter。

---

## 9. 测试策略

- 单元测试：top_k、score_threshold、token compression。
- 集成测试：fake retriever 返回多资源结果。
- 安全测试：返回未授权 resource_id 时抛错。
- 降级测试：空结果返回空 chunks 和可解释 prompt。

---

## 10. 检查清单

- [ ] RetrievalEngine 已实现
- [ ] 输出兼容 `RetrievalResult`
- [ ] 权限防御校验已实现
- [ ] 空结果降级已实现
- [ ] 测试覆盖率 80%+
