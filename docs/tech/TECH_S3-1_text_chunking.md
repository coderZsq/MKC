# 技术文档：[S3-1] 文本分块策略实现

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S3-1_text_chunking.md](../prd/PRD_S3-1_text_chunking.md)

---

## 1. 文档目标

定义 AI Service 中文本分块模块的技术实现：策略接口、三种分块器实现、Chunk 数据模型、配置加载与测试策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- pydantic 2.x
- tiktoken 0.7.x
- PyYAML 6.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/chunk` | Internal API Key | 对文本分块（内部/测试用） |

### 请求示例

```json
POST /ai/v1/chunk
Headers: X-Internal-Key: <key>
{
  "resource_id": "01922b9c-...",
  "text": "第一章...\n\n第二章...",
  "metadata": {"page": 1},
  "strategy": "paragraph"
}
```

### 响应示例

```json
{
  "chunks": [
    {
      "id": "chunk-uuid",
      "resource_id": "01922b9c-...",
      "index": 0,
      "text": "第一章...",
      "start_pos": 0,
      "end_pos": 120,
      "metadata": {"page": 1},
      "token_count": 45
    }
  ]
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | INVALID_STRATEGY | 不支持的分块策略 |
| 400 | EMPTY_TEXT | 输入文本为空 |
| 500 | CHUNKING_ERROR | 分块内部错误 |

---

## 4. 配置

新增 `config/ai.yaml` 分块配置段：

```yaml
chunking:
  strategy: paragraph
  chunk_size: 512
  chunk_overlap: 50
  separators: ["\n## ", "\n# ", "\n\n", "\n", "。", "，", " ", ""]
  preserve_metadata: true
```

环境变量：

- `CHUNKING_DEFAULT_STRATEGY`：默认策略
- `CHUNKING_CHUNK_SIZE`：默认块大小

---

## 5. 模块设计

### 5.1 ChunkingService

```python
class ChunkingService:
    def __init__(self, config: ChunkingConfig):
        self._chunkers: dict[str, BaseChunker] = {
            "paragraph": ParagraphChunker(config),
            "fixed_token": FixedTokenChunker(config),
            "semantic": SemanticChunker(config),
        }

    def chunk(self, text: str, resource_id: str, metadata: dict, strategy: str | None = None) -> list[Chunk]:
        strategy = strategy or self._config.default_strategy
        chunker = self._chunkers.get(strategy)
        if not chunker:
            raise InvalidStrategyError(strategy)
        return chunker.split(text, resource_id, metadata)
```

### 5.2 BaseChunker

```python
class BaseChunker(ABC):
    def __init__(self, config: ChunkingConfig): ...

    @abstractmethod
    def split(self, text: str, resource_id: str, metadata: dict) -> list[Chunk]: ...
```

### 5.3 ParagraphChunker

- 按空行分割段落
- 对超长段落递归拆分到 chunk_size

### 5.4 FixedTokenChunker

- 使用 tiktoken 估算 token
- 按 chunk_size 切分，保留 chunk_overlap

### 5.5 SemanticChunker

- 使用分隔符列表从粗到细切分
- 优先保留章节标题边界

---

## 6. 关键代码实现

### 6.1 Chunk 模型

```python
from pydantic import BaseModel

class Chunk(BaseModel):
    id: str
    resource_id: str
    index: int
    text: str
    start_pos: int
    end_pos: int
    metadata: dict
    token_count: int
```

### 6.2 固定 token 分块

```python
import tiktoken

class FixedTokenChunker(BaseChunker):
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def split(self, text: str, resource_id: str, metadata: dict) -> list[Chunk]:
        tokens = self._encoder.encode(text)
        chunks = []
        start = 0
        index = 0
        while start < len(tokens):
            end = min(start + self._config.chunk_size, len(tokens))
            chunk_text = self._encoder.decode(tokens[start:end])
            chunks.append(Chunk(
                id=f"{resource_id}-{index}",
                resource_id=resource_id,
                index=index,
                text=chunk_text,
                start_pos=start,
                end_pos=end,
                metadata=metadata,
                token_count=len(tokens[start:end]),
            ))
            start = end - self._config.chunk_overlap
            if start < 0:
                start = 0
            if start == end:
                break
            index += 1
        return chunks
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 不支持策略 | 400 | INVALID_STRATEGY | 不支持的分块策略 |
| 输入为空 | 400 | EMPTY_TEXT | 输入文本为空 |
| tiktoken 加载失败 | 500 | TOKENIZER_ERROR | 分词器加载失败 |

---

## 8. Web 端适配要点

分块接口为内部接口，Web 端不直接调用。分块策略影响后续检索与答案质量，间接影响 Web 端用户体验。

---

## 9. 测试策略

- **单元测试**：三种分块器边界条件、空文本、重叠窗口、元数据保留
- **集成测试**：调用 `/ai/v1/chunk` 接口验证响应格式
- **Mock 策略**：使用固定文本验证输出顺序与 token 估算

---

## 10. 检查清单

- [ ] `ChunkingService` 统一入口
- [ ] 三种分块器实现
- [ ] `Chunk` 数据模型与元数据保留
- [ ] 配置化策略与参数
- [ ] 错误处理与降级
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
