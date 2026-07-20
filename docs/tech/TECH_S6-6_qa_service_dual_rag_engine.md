# 技术文档：[S6-6] 将 QA Service 接入可切换 RAG Engine

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-6_qa_service_dual_rag_engine.md](../prd/PRD_S6-6_qa_service_dual_rag_engine.md)

---

## 1. 文档目标

定义 QA Service 接入 legacy/LlamaIndex 双 RAG 引擎的 factory、接口、错误处理和测试策略，保证 SSE 与 citation 契约不变。

---

## 2. 技术栈

- Python 3.11+
- Flask SSE
- pydantic 2.x
- LlamaIndex retrieval engine
- pytest / pytest-asyncio

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/qa/stream` | Internal API Key | 流式问答，内部可切 RAG 引擎 |

请求/响应不新增字段。`RAG_ENGINE` 只在服务端生效。

---

## 4. 配置

```bash
RAG_ENGINE=legacy
# 或
RAG_ENGINE=llamaindex
```

---

## 5. 模块设计

- `RagEngine` protocol：统一 retrieve 方法。
- `LegacyRagEngine`：包装现有 `RetrievalService`。
- `LlamaIndexRagEngine`：包装 S6-5 retrieval engine。
- `RagEngineFactory`：根据配置构建实现。
- `QAService`：依赖 `RagEngine`，不直接依赖具体实现。

---

## 6. 关键代码实现

```python
class QAService:
    def __init__(self, rag_engine: RagEngine, llm_client: LLMClient, ...):
        self._rag = rag_engine

    async def stream_answer(self, request: QARequest):
        if request.resource_ids:
            try:
                retrieval_result = self._rag.retrieve(RetrievalRequest(...))
            except APIException as exc:
                yield self._error_event(request, exc.code, exc.message)
                return
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| RAG 引擎不可用 | 503 | RAG_ENGINE_UNAVAILABLE | RAG 引擎不可用 |
| 检索不可用 | 503 | RETRIEVAL_UNAVAILABLE | 检索不可用 |
| 流式生成失败 | 500 | LLM_STREAM_ERROR | 流式生成失败 |

---

## 8. Web 端适配要点

Web Chat 接口不变。测试应在两种引擎下验证 `chunk/citation/done` 渲染。

---

## 9. 测试策略

- 参数化测试：legacy 与 llamaindex 两种 engine。
- QA Service 测试：成功、空结果、检索异常、LLM 异常。
- SSE 兼容测试：事件类型和字段不变。
- 回归测试：现有 QA tests 在 legacy 模式通过。

---

## 10. 检查清单

- [ ] `RagEngine` protocol 已实现
- [ ] Factory 已实现
- [ ] QA Service 改为依赖统一接口
- [ ] 双引擎测试通过
- [ ] SSE/citation 兼容
