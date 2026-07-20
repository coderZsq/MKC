# 技术文档：[S6-1] 梳理现有 RAG 链路并定义 LlamaIndex 迁移边界

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-1_rag_migration_boundary.md](../prd/PRD_S6-1_rag_migration_boundary.md)

---

## 1. 文档目标

定义 S6 LlamaIndex 迁移的系统边界、保留契约、可替换模块、风险清单和回滚策略，为后续 S6-2 到 S6-8 提供统一技术基线。

---

## 2. 技术栈

- Python 3.11+
- Flask / Celery
- Milvus / pymilvus
- LlamaIndex 0.10+ / 0.11+
- pydantic 2.x
- pytest 8.x

---

## 3. 接口契约

本任务不新增运行时接口，只冻结既有契约。

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/qa/stream` | Internal API Key | QA SSE 内部接口，S6 必须兼容 |
| POST | `/api/v1/conversations/{id}/ask` | Bearer JWT | Gateway 对外问答接口，不因 S6 改动 |
| CLI | `python -m eval.pipeline` | 本地环境变量 | S5 评估流水线，S6-7 复用 |

SSE 事件类型保持：`chunk`、`reasoning`、`citation`、`done`、`error`。

---

## 4. 配置

S6 统一以 `RAG_ENGINE` 作为切换入口：

```yaml
rag:
  engine: "${RAG_ENGINE:-legacy}"
  allowed_engines:
    - legacy
    - llamaindex
```

---

## 5. 模块设计

- 保持不变：Gateway API、Flutter Chat、SSE event schema、citation event schema、conversation persistence。
- 可替换：AI Service 内部 retrieval engine、node mapping、Milvus adapter、context assembly。
- 评估复用：S5 eval dataset、LLM-as-judge pipeline、report writer。
- 回滚方式：设置 `RAG_ENGINE=legacy` 后重启 AI Service。

---

## 6. 关键代码实现

```python
class RagEngine(Protocol):
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Return chunks and prompt using a stable MKC retrieval contract."""


def build_rag_engine(config: RagEngineConfig) -> RagEngine:
    if config.engine == "legacy":
        return LegacyRagEngine(...)
    if config.engine == "llamaindex":
        return LlamaIndexRagEngine(...)
    raise RagEngineConfigError(f"unsupported RAG_ENGINE={config.engine}")
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 非法 RAG_ENGINE | N/A | RAG_ENGINE_INVALID | RAG 引擎配置不合法 |
| LlamaIndex 不可用 | 503 | RAG_ENGINE_UNAVAILABLE | RAG 引擎不可用 |
| metadata 映射失败 | 500 | RAG_METADATA_INVALID | 检索元数据不合法 |

---

## 8. Web 端适配要点

Flutter Web 无需新增配置。验收时需通过同一 Web Chat 页面分别验证 legacy 与 LlamaIndex 模式。

---

## 9. 测试策略

- 静态测试：文档包含迁移边界、保留契约和回滚策略。
- 架构 review：检查后续 S6 任务是否遵守同一契约。
- 文档检查：markdownlint。

---

## 10. 检查清单

- [ ] RAG 现状链路已梳理
- [ ] 保留契约已明确
- [ ] 迁移范围已明确
- [ ] 回滚策略已明确
- [ ] 风险清单已明确
