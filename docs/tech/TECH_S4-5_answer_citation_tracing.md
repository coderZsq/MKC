# 技术文档：[S4-5] 答案引用溯源（时间戳/页码）

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S4-5_answer_citation_tracing.md](../prd/PRD_S4-5_answer_citation_tracing.md)

---

## 1. 文档目标

定义 AI Service 中答案引用溯源模块的技术实现：引用标记 Prompt 构建、`[^n]` 标记解析与 chunk metadata 映射、幻觉引用校验剔除、SSE `citation` 事件下发与测试策略。复用 S3-4 检索结果与 S3-6 SSE 问答链路，不新增对外端点。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- pydantic 2.x
- Jinja2 3.1.x
- zhipuai 2.x（GLM-4 / glm-4-flash）/ openai 1.30+（Kimi）
- tiktoken 0.7.x

---

## 3. 接口契约

本任务不新增对外端点，扩展 S3-6 的 `POST /ai/v1/qa/stream`（Internal API Key）响应，在 `done` 事件前新增 `citation` 事件。

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/qa/stream` | Internal API Key | 流式问答生成，新增 `citation` 事件 |

### SSE 事件示例

```text
event: chunk
data: {"message_id":"msg-1","conversation_id":"conv-1","delta":"本次会议主要讨论了产品路线图 [^1]","index":0}

event: citation
data: {"message_id":"msg-1","chunk_id":"chunk-7","resource_id":"res-1","resource_type":"audio","timestamp_start":120.5,"timestamp_end":145.0,"score":0.89,"snippet":"产品路线图与下迭代交付节点..."}

event: citation
data: {"message_id":"msg-1","chunk_id":"chunk-3","resource_id":"res-2","resource_type":"pdf","page":3,"score":0.84,"snippet":"下个迭代的交付节点定于..."}

event: done
data: {"message_id":"msg-1","finish_reason":"stop","citation_count":2}
```

### citation 事件字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| message_id | string | 是 | 答案消息 ID |
| chunk_id | string | 是 | 来源 chunk ID |
| resource_id | string | 是 | 资源 ID |
| resource_type | string | 是 | `audio` / `pdf` |
| page | int | 否 | PDF 页码（resource_type=pdf 时返回） |
| timestamp_start | float | 否 | 音频起始秒（resource_type=audio 时返回） |
| timestamp_end | float | 否 | 音频结束秒（resource_type=audio 时返回） |
| score | float | 是 | 检索相似度分数 |
| snippet | string | 否 | 来源原文片段（截断 200 字符） |

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | INVALID_REQUEST | 缺少 question 或 resource_ids |
| 403 | FORBIDDEN | 无权访问资源 |
| 503 | RETRIEVAL_UNAVAILABLE | 检索服务不可用 |
| 504 | LLM_TIMEOUT | LLM 生成超时 |

---

## 4. 配置

扩展 `config/ai.yaml`，新增 `citation` 配置段：

```yaml
citation:
  enabled: true
  max_citations: 8                 # 单答案引用数上限
  snippet_max_chars: 200           # snippet 截断长度
  marker_pattern: "\\[\\^(\\d+)\\]" # [^n] 正则
  prompt_template: "prompts/rag_citation.txt"
  drop_ungrounded: true            # 剔除无依据引用
  log_dropped: true                # 记录被剔除标记
```

---

## 5. 模块设计

### 5.1 Citation 数据模型

```python
class Citation(BaseModel):
    index: int                      # 引用序号 [^n] 中的 n
    chunk_id: str
    resource_id: str
    resource_type: Literal["audio", "pdf"]
    page: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    score: float
    snippet: str | None = None
```

### 5.2 CitationFormatter

```python
class CitationFormatter:
    def __init__(self, marker_pattern: str, snippet_max_chars: int):
        self._pattern = re.compile(marker_pattern)
        self._snippet_max_chars = snippet_max_chars

    def format(self, answer: str, chunks: list[Chunk]) -> tuple[str, list[Citation]]:
        """将答案中的 [^n] 标记映射到 chunks[n-1] 的 metadata。
        返回剔除无效标记后的答案与有序 citations 列表。"""
```

### 5.3 CitationValidator

```python
class CitationValidator:
    def __init__(self, max_citations: int, log_dropped: bool):
        self._max_citations = max_citations
        self._log_dropped = log_dropped

    def validate(self, citations: list[Citation], authorized_resource_ids: set[str]) -> list[Citation]:
        """校验引用：剔除越权资源、越序标记，按上限截断。"""
```

### 5.4 CitationService

```python
class CitationService:
    def __init__(self, formatter: CitationFormatter, validator: CitationValidator):
        self._formatter = formatter
        self._validator = validator

    def build_citations(self, answer: str, chunks: list[Chunk], authorized_resource_ids: set[str]) -> CitationResult:
        """编排：格式化 -> 校验，返回最终答案与 citations。"""
```

---

## 6. 关键代码实现

### 6.1 带引用指示的 Prompt 模板

```jinja2
你是知识库助手。请基于以下上下文回答用户问题。
规则：
1. 引用上下文片段时，在句末使用 [^n] 标记，n 为片段序号。
2. 仅引用下方提供的片段，不得编造来源。
3. 多处引用同一片段时复用同一序号。

上下文：
{% for chunk in chunks %}
[^{{ loop.index }}] {{ chunk.text }} （来源：{{ chunk.metadata }}）
{% endfor %}

用户问题：{{ question }}
请给出简洁、准确的回答。
```

### 6.2 标记映射与校验

```python
import re

class CitationFormatter:
    def format(self, answer: str, chunks: list[Chunk]) -> tuple[str, list[Citation]]:
        citations: list[Citation] = []
        used_indices: set[int] = set()
        for match in self._pattern.finditer(answer):
            n = int(match.group(1))
            if n < 1 or n > len(chunks) or n in used_indices:
                continue
            chunk = chunks[n - 1]
            citations.append(Citation(
                index=n,
                chunk_id=chunk.id,
                resource_id=chunk.resource_id,
                resource_type=chunk.metadata.get("resource_type", "pdf"),
                page=chunk.metadata.get("page"),
                timestamp_start=chunk.metadata.get("timestamp_start"),
                timestamp_end=chunk.metadata.get("timestamp_end"),
                score=chunk.score,
                snippet=self._truncate(chunk.text),
            ))
            used_indices.add(n)
        return answer, citations

    def _truncate(self, text: str) -> str:
        return text[: self._snippet_max_chars]


class CitationValidator:
    def validate(self, citations: list[Citation], authorized_resource_ids: set[str]) -> list[Citation]:
        valid: list[Citation] = []
        for c in citations:
            if c.resource_id not in authorized_resource_ids:
                self._log("drop_unauthorized", c.index)
                continue
            valid.append(c)
        return valid[: self._max_citations]
```

### 6.3 SSE citation 事件下发

```python
async def stream_answer(self, request: QARequest):
    retrieval_result = await self._retrieval_service.retrieve(
        RetrievalRequest(question=request.question, ...)
    )
    authorized = {c.resource_id for c in retrieval_result.chunks}
    messages = self._build_messages(request.history, retrieval_result.prompt)
    answer_buf = []
    async for chunk in self._llm_client.stream_complete(LLMRequest(messages=messages)):
        answer_buf.append(chunk.delta)
        yield SseEvent(type="chunk", data={"delta": chunk.delta})

    answer = "".join(answer_buf)
    clean_answer, citations = self._citation_service.build_citations(
        answer, retrieval_result.chunks, authorized
    )
    for citation in citations:
        yield SseEvent(type="citation", data=citation.model_dump())
    yield SseEvent(type="done", data={"finish_reason": "stop", "citation_count": len(citations)})
```

### 6.4 时间戳格式化（mm:ss）

```python
def format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 缺少 question | 400 | INVALID_REQUEST | 缺少问题 |
| 资源越权 | 403 | FORBIDDEN | 无权访问资源 |
| LLM 未生成引用 | 200 | - | 正常返回，citation_count=0 |
| chunk metadata 缺失 | 200 | - | 引用仅返回 resource_id 与 score |
| 引用映射异常 | 200 | - | 降级无引用模式，记录 ERROR |
| LLM 超时 | 504 | LLM_TIMEOUT | 生成超时 |

---

## 8. Web 端适配要点

- SSE 解析新增 `citation` 事件分支，复用 S3-6 事件分发器
- Flutter `CitationCard` 按 `resource_type` 渲染：audio 显示 `mm:ss`，pdf 显示“第 N 页”
- `[^n]` 脚注与 `CitationCard` 序号联动，点击跳转交由 S4-6 实现
- Web 端 `EventSource` 解析逻辑与移动端一致，无额外适配

---

## 9. 测试策略

- **单元测试**：`CitationFormatter` 标记映射、`CitationValidator` 剔除与截断、`CitationService` 编排、时间戳格式化
- **集成测试**：mock 检索与 LLM 验证完整 SSE 链路，断言 `citation` 事件字段与顺序
- **Mock 策略**：固定 LLM 返回带 `[^n]` 的答案与固定 chunk 列表，覆盖音频/PDF 两种 resource_type
- **边界用例**：无引用、越序标记、metadata 缺失、引用数超上限、越权资源

---

## 10. 检查清单

- [ ] `CitationService` 编排：格式化 + 校验
- [ ] `CitationFormatter` `[^n]` 标记映射
- [ ] `CitationValidator` 幻觉剔除与越权过滤
- [ ] 带引用指示的 Prompt 模板
- [ ] SSE `citation` 事件下发
- [ ] 音频时间戳 / PDF 页码引用
- [ ] 权限校验复用 S3-4 过滤结果
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
