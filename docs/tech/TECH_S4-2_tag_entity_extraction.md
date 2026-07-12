# 技术文档：[S4-2] 实现标签/实体抽取

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S4-2_tag_entity_extraction.md](../prd/PRD_S4-2_tag_entity_extraction.md)

---

## 1. 文档目标

定义标签/实体抽取模块的技术实现：LLM JSON mode 抽取、标签去重归一化、实体归一化、规则降级、异步任务调度、分层存储与接口契约、错误映射与测试策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- Celery 5.4.x
- zhipuai 2.x / openai 1.30+
- tenacity 8.x
- pydantic 2.x
- MySQL（标签/实体持久化）
- 正则表达式（规则降级抽取）

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/resources/{resource_id}/extract-tags` | X-Internal-Key | 内部异步触发抽取 |
| GET | `/api/v1/resources/{id}/tags` | Bearer JWT | Gateway 查询标签与实体 |

### 请求示例

```json
POST /ai/v1/resources/res_abc123/extract-tags
Headers: X-Internal-Key: <key>
{
  "content": "本次会议由张三主持，讨论了机器学习模型训练的数据集选取……",
  "source_type": "audio"
}
```

### 响应示例

```json
{
  "resource_id": "res_abc123",
  "tags": [
    {"tag": "机器学习", "source": "llm"},
    {"tag": "模型训练", "source": "llm"}
  ],
  "entities": [
    {"entity": "张三", "type": "PERSON", "mention": "张三"},
    {"entity": "OpenAI", "type": "ORG", "mention": "OpenAI"}
  ],
  "source": "llm",
  "fallback": false
}
```

### Gateway 响应示例

```json
GET /api/v1/resources/res_abc123/tags
Headers: Authorization: Bearer <jwt>
{
  "resource_id": "res_abc123",
  "tags": ["机器学习", "模型训练", "数据集"],
  "entities": [
    {"entity": "张三", "type": "PERSON", "mention": "张三"},
    {"entity": "OpenAI", "type": "ORG", "mention": "OpenAI"}
  ]
}
```

### 错误码

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 资源内容为空 | 400 | EMPTY_CONTENT | 资源内容为空，无法抽取 |
| 内部 Key 无效 | 401 | UNAUTHORIZED | 内部 Key 认证失败 |
| 资源不存在 | 404 | RESOURCE_NOT_FOUND | 资源不存在 |
| LLM 返回非法 JSON | 500 | LLM_INVALID_JSON | LLM 输出非法 JSON，已降级为规则抽取 |
| LLM 调用失败 | 503 | LLM_UNAVAILABLE | LLM 服务不可用，已降级为规则抽取 |
| LLM 调用超时 | 504 | LLM_TIMEOUT | LLM 调用超时，已降级为规则抽取 |

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
extraction:
  enabled: true
  llm:
    provider: zhipuai
    model: glm-4-flash
    api_key: "${ZHIPU_API_KEY}"
    base_url: "https://open.bigmodel.cn/api/paas/v4"
    temperature: 0.1
    max_tokens: 1024
    timeout: 60
    response_format: json_object
    max_retries: 3
  tags:
    min_count: 5
    max_count: 10
    normalize_lowercase: false
    synonym_merge: true
  entities:
    allowed_types:
      - PERSON
      - ORG
      - DATE
      - LOC
      - GPE
      - MISC
  fallback:
    enabled: true
    provider: rule
  batch:
    max_chars: 4000
```

---

## 5. 模块设计

### 5.1 Storage 层

```python
class TagStorage:
    def save_tags(self, resource_id: str, tags: list[TagRecord]) -> None: ...
    def get_tags(self, resource_id: str) -> list[TagRecord]: ...

class EntityStorage:
    def save_entities(self, resource_id: str, entities: list[EntityRecord]) -> None: ...
    def get_entities(self, resource_id: str) -> list[EntityRecord]: ...
```

### 5.2 Repository 层

```python
class TagRepository:
    def upsert(self, resource_id: str, tags: list[Tag]) -> list[TagRecord]: ...
    def find_by_resource(self, resource_id: str) -> list[TagRecord]: ...
    def delete_by_resource(self, resource_id: str) -> None: ...

class EntityRepository:
    def upsert(self, resource_id: str, entities: list[Entity]) -> list[EntityRecord]: ...
    def find_by_resource(self, resource_id: str) -> list[EntityRecord]: ...
    def delete_by_resource(self, resource_id: str) -> None: ...
```

### 5.3 Provider 层

```python
class BaseExtractionProvider:
    def extract(self, content: str) -> ExtractionResult: ...

class LLMExtractionProvider(BaseExtractionProvider):
    def __init__(self, client, config: LLMConfig): ...
    def extract(self, content: str) -> ExtractionResult: ...

class RuleExtractionProvider(BaseExtractionProvider):
    def __init__(self, config: RuleConfig): ...
    def extract(self, content: str) -> ExtractionResult: ...
```

### 5.4 Service 层

```python
class ExtractionService:
    def __init__(
        self,
        llm_provider: LLMExtractionProvider,
        rule_provider: RuleExtractionProvider,
        tag_normalizer: TagNormalizer,
        entity_resolver: EntityResolver,
        tag_repository: TagRepository,
        entity_repository: EntityRepository,
        config: ExtractionConfig,
    ): ...
    def extract(self, resource_id: str, content: str) -> ExtractionResponse: ...
```

### 5.5 Handler 层

```python
class ExtractionHandler:
    def extract_tags(self, resource_id: str, request: ExtractRequest) -> ExtractResponse: ...
    def get_tags(self, resource_id: str) -> TagsResponse: ...
```

### 5.6 数据模型

```python
class Tag(BaseModel):
    tag: str
    source: Literal["llm", "rule"] = "llm"

class Entity(BaseModel):
    entity: str
    type: Literal["PERSON", "ORG", "DATE", "LOC", "GPE", "MISC"]
    mention: str

class ExtractionResult(BaseModel):
    tags: list[str]
    entities: list[Entity]
    source: Literal["llm", "rule"]

class ExtractionResponse(BaseModel):
    resource_id: str
    tags: list[Tag]
    entities: list[Entity]
    source: Literal["llm", "rule"]
    fallback: bool
```

---

## 6. 关键代码实现

### 6.1 LLM JSON mode 抽取

```python
import json
from tenacity import retry, stop_after_attempt, wait_exponential

EXTRACTION_PROMPT = """你是一名信息抽取专家。请从以下文本中抽取关键词标签与命名实体。

要求：
- 标签：5-10 个关键词，反映文本核心主题
- 实体：类型仅限 PERSON/ORG/DATE/LOC/GPE/MISC，每条包含归一化值 text 与原文 mention

仅输出 JSON，格式如下：
{{"tags": ["..."], "entities": [{{"text": "...", "type": "PERSON", "mention": "..."}}]}}

文本：
{content}"""

class LLMExtractionProvider(BaseExtractionProvider):
    def __init__(self, client, config: LLMConfig):
        self._client = client
        self._config = config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    def extract(self, content: str) -> ExtractionResult:
        prompt = EXTRACTION_PROMPT.format(content=content[: self._config.batch_max_chars])
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return self._parse(data)

    def _parse(self, data: dict) -> ExtractionResult:
        tags = [str(t).strip() for t in data.get("tags", [])]
        entities = []
        allowed = {"PERSON", "ORG", "DATE", "LOC", "GPE", "MISC"}
        for e in data.get("entities", []):
            etype = e.get("type", "").upper()
            if etype not in allowed:
                continue
            entities.append(Entity(
                entity=e.get("text", "").strip(),
                type=etype,
                mention=e.get("mention", "").strip(),
            ))
        return ExtractionResult(tags=tags, entities=entities, source="llm")
```

### 6.2 标签去重与归一化

```python
SYNONYM_MAP = {
    "ai": "人工智能",
    "ml": "机器学习",
    "nlp": "自然语言处理",
}

class TagNormalizer:
    def __init__(self, config: TagConfig):
        self._min = config.min_count
        self._max = config.max_count
        self._lowercase = config.normalize_lowercase
        self._synonyms = SYNONYM_MAP if config.synonym_merge else {}

    def normalize(self, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in tags:
            normalized = tag.strip()
            if self._lowercase:
                normalized = normalized.lower()
            normalized = self._synonyms.get(normalized.lower(), normalized)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
            if len(result) >= self._max:
                break
        return result
```

### 6.3 规则降级抽取

```python
import re

DATE_PATTERN = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{2}-\d{2}")
ORG_PATTERN = re.compile(r"[一-龥A-Za-z]+公司|[一-龥]+大学|OpenAI|Google|Microsoft")

class RuleExtractionProvider(BaseExtractionProvider):
    def extract(self, content: str) -> ExtractionResult:
        entities: list[Entity] = []
        for m in DATE_PATTERN.finditer(content):
            entities.append(Entity(entity=m.group(), type="DATE", mention=m.group()))
        for m in ORG_PATTERN.finditer(content):
            entities.append(Entity(entity=m.group(), type="ORG", mention=m.group()))
        tags = self._extract_keywords(content)
        return ExtractionResult(tags=tags, entities=entities, source="rule")

    def _extract_keywords(self, content: str) -> list[str]:
        # 基于词频的简易关键词抽取
        words = re.findall(r"[一-龥]{2,4}|[A-Za-z]{3,}", content)
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:10]]
```

### 6.4 Service 编排与降级

```python
class ExtractionService:
    def extract(self, resource_id: str, content: str) -> ExtractionResponse:
        if not content or not content.strip():
            return self._empty_response(resource_id, fallback=True)

        try:
            result = self._llm_provider.extract(content)
            source = "llm"
            fallback = False
        except (json.JSONDecodeError, Exception):
            if not self._config.fallback_enabled:
                raise
            result = self._rule_provider.extract(content)
            source = "rule"
            fallback = True

        tags = self._tag_normalizer.normalize(result.tags)
        entities = self._entity_resolver.resolve(result.entities)

        tag_records = self._tag_repository.upsert(resource_id, [Tag(tag=t, source=source) for t in tags])
        entity_records = self._entity_repository.upsert(resource_id, entities)

        return ExtractionResponse(
            resource_id=resource_id,
            tags=[Tag(tag=r.tag, source=r.source) for r in tag_records],
            entities=[Entity(entity=r.entity, type=r.type, mention=r.mention) for r in entity_records],
            source=source,
            fallback=fallback,
        )

    def _empty_response(self, resource_id: str, fallback: bool) -> ExtractionResponse:
        return ExtractionResponse(
            resource_id=resource_id,
            tags=[],
            entities=[],
            source="rule",
            fallback=fallback,
        )
```

### 6.5 Celery 异步任务

```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def extract_tags_task(self, resource_id: str, content: str):
    service = build_extraction_service()
    try:
        response = service.extract(resource_id, content)
        return response.model_dump()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 资源内容为空 | 400 | EMPTY_CONTENT | 资源内容为空，无法抽取 |
| 内部 Key 无效 | 401 | UNAUTHORIZED | 内部 Key 认证失败 |
| 资源不存在 | 404 | RESOURCE_NOT_FOUND | 资源不存在 |
| LLM 返回非法 JSON | 500 | LLM_INVALID_JSON | LLM 输出非法 JSON，已降级为规则抽取 |
| LLM 调用失败 | 503 | LLM_UNAVAILABLE | LLM 服务不可用，已降级为规则抽取 |
| LLM 调用超时 | 504 | LLM_TIMEOUT | LLM 调用超时，已降级为规则抽取 |
| 数据库写入失败 | 500 | DB_WRITE_FAILED | 标签/实体存储失败 |

---

## 8. Web 端适配要点

- Web 端通过 Gateway `GET /api/v1/resources/{id}/tags` 获取标签与实体，不直接调用 AI Service
- 资源卡片（S4-3）以标签云与实体列表形式展示，抽取未完成时展示骨架占位
- 标签可点击触发按标签检索过滤
- `fallback: true` 时卡片可标注「规则抽取」提示，便于用户区分质量

---

## 9. 测试策略

- **单元测试**：`TagNormalizer` 去重/归一化/截断、`EntityResolver` 归一化、`LLMExtractionProvider` JSON 解析与非法类型过滤、`RuleExtractionProvider` 正则抽取、`ExtractionService` 降级编排
- **集成测试**：内部接口 `POST /ai/v1/resources/{id}/extract-tags` 端到端、Gateway `GET /api/v1/resources/{id}/tags` 查询、Celery 异步任务触发
- **Mock 策略**：Mock LLM 返回合法/非法 JSON，验证重试与降级路径
- **覆盖率**：目标 80%+，ruff / mypy 静态检查通过

---

## 10. 检查清单

- [ ] LLM JSON mode 抽取标签与实体
- [ ] 标签去重、归一化、数量限制
- [ ] 实体类型校验（PERSON/ORG/DATE/LOC/GPE/MISC）
- [ ] 规则降级抽取
- [ ] LLM 非法 JSON 重试 + 降级
- [ ] 空内容兜底
- [ ] `resource_tags` / `resource_entities` 存储
- [ ] 内部接口 X-Internal-Key 认证
- [ ] Gateway 接口 Bearer JWT 认证
- [ ] Celery 异步任务
- [ ] 测试覆盖率 80%+
- [ ] ruff / mypy 通过
- [ ] 无硬编码密钥
- [ ] OpenAPI/文档同步更新
