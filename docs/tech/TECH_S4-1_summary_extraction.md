# 技术文档：[S4-1] 实现全文/章节摘要提取

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S4-1_summary_extraction.md](../prd/PRD_S4-1_summary_extraction.md)

---

## 1. 文档目标

定义全文/章节摘要提取的技术实现：Celery 异步触发、章节边界划分、map-reduce 长文档摘要、Jinja2 Prompt + JSON mode 结构化输出、`summaries` 表持久化、重试与降级、接口契约与测试策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- Celery 5.4+ + Redis 7.x
- 智谱 GLM-4（zhipuai 2.x，model `glm-4-flash`）/ Kimi（openai 1.30+）
- Jinja2 3.1.x（Prompt 模板）
- tiktoken 0.7.x（token 估算与分块）
- tenacity 8.x（重试）
- pydantic 2.x（数据模型）
- MinIO（全文摘要 JSON 存储）/ MySQL via Gateway GORM（`summaries` 表）

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/resources/{resource_id}/summarize` | X-Internal-Key | 触发摘要生成（异步，202） |
| POST | `/api/v1/internal/resources/{resource_id}/summaries` | X-Internal-Key | AI Service 持久化摘要到 `summaries` 表 |
| GET | `/api/v1/resources/{id}/summary` | Bearer JWT | 前端查询资源摘要 |

### 请求示例

```text
POST /ai/v1/resources/01922b9c-.../summarize
Headers: X-Internal-Key: <key>
{
  "types": ["full", "section"],
  "source_type": "pdf"
}
```

### 响应示例

```json
{
  "success": true,
  "data": {
    "task_id": "sum-01922b9c-...",
    "status": "pending"
  }
}
```

```json
GET /api/v1/resources/01922b9c-.../summary
Authorization: Bearer <jwt>
{
  "success": true,
  "data": {
    "resource_id": "01922b9c-...",
    "full_summary": "本文档介绍了 MKC 多媒体知识库助手的整体架构……",
    "sections": [
      {"title": "第一章 概述", "summary": "本章介绍了系统目标……", "page_range": [1, 3]}
    ],
    "model": "glm-4-flash",
    "fallback": false,
    "updated_at": "2026-07-12T10:00:00Z"
  }
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 401 | INTERNAL_AUTH_FAILED | 内部 Key 校验失败 |
| 401 | UNAUTHORIZED | Gateway JWT 缺失或失效 |
| 404 | RESOURCE_NOT_FOUND | 资源不存在或无权访问 |
| 409 | SUMMARY_IN_PROGRESS | 摘要任务进行中，避免重复触发 |
| 422 | SUMMARY_PARSE_FAILED | LLM 输出解析失败 |
| 500 | SUMMARY_GENERATION_FAILED | 摘要生成失败 |
| 504 | LLM_TIMEOUT | LLM 调用超时 |

---

## 4. 配置

新增 `config/ai.yaml` 的 `summary` 段：

```yaml
summary:
  enabled: true
  full_summary_chars: [200, 300]        # 全文摘要字数范围
  section_summary_chars: [80, 150]      # 章节摘要字数范围
  map_reduce:
    enabled: true
    chunk_token_limit: 3000             # 单段 token 上限
    overlap_tokens: 100
  llm:
    model: glm-4-flash
    temperature: 0.3
    max_tokens: 1024
    response_format: json               # json / function_calling
    max_retries: 3
    timeout: 60
  fallback:
    empty_summary_chars: 200            # 摘要为空时取前 N 字
    on_section_split_fail: full_only    # 降级为仅全文摘要
  storage:
    minio_bucket: results
    persist_endpoint: "/api/v1/internal/resources/{resource_id}/summaries"
```

---

## 5. 模块设计

### 5.1 Storage 层（数据模型）

```python
class SectionSummary(BaseModel):
    title: str
    summary: str
    page_range: list[int] | None = None
    timestamp_range: list[float] | None = None

class SummaryResult(BaseModel):
    resource_id: str
    full_summary: str | None = None
    sections: list[SectionSummary] = []
    model: str
    fallback: bool = False
    tokens: int = 0
    created_at: datetime
```

### 5.2 Repository 层

```python
class SummaryRepository:
    def save(self, resource_id: str, result: SummaryResult) -> None: ...
    def get(self, resource_id: str) -> SummaryResult | None: ...
    def delete(self, resource_id: str) -> None: ...   # 重新生成时清空旧摘要
```

### 5.3 Service 层

```python
class SummaryService:
    def generate(self, resource_id: str, source_type: str,
                 types: list[str]) -> SummaryResult: ...

class MapReduceSummarizer:
    def summarize(self, text: str) -> str: ...

class SectionSplitter:
    def split_pdf(self, parsed: dict) -> list[SectionSummary]: ...
    def split_audio(self, srt_segments: list[dict]) -> list[SectionSummary]: ...
```

### 5.4 Handler 层

```python
class SummaryHandler:
    def trigger(self, resource_id: str, payload: SummarizeRequest) -> dict: ...
```

### 5.5 Provider 层

```python
class SummaryLLMProvider:
    """复用 S3-5 LLMClient，封装 Jinja2 Prompt 渲染与 JSON mode 解析"""
    def summarize_full(self, content: str) -> str: ...
    def summarize_chunk(self, content: str) -> str: ...
    def summarize_section(self, title: str, content: str) -> str: ...
```

### 5.6 Celery 任务

```python
@app.task(bind=True, base=BaseAITask)
def run_summarize(self, resource_id: str, payload: dict): ...
```

---

## 6. 关键代码实现

### 6.1 Jinja2 Prompt 模板

`app/prompts/full_summary.j2`：

```text
你是文档摘要专家。请为以下文档生成 {{ min_chars }}-{{ max_chars }} 字的中文摘要，概括核心内容与结论，不要罗列细节。
只输出 JSON：{"summary": "<摘要内容>"}

文档内容：
{{ content }}
```

`app/prompts/section_summary.j2`：

```text
你是文档摘要专家。请为以下章节生成 {{ min_chars }}-{{ max_chars }} 字的中文摘要。
章节标题：{{ section_title }}
只输出 JSON：{"summary": "<摘要内容>"}

章节内容：
{{ content }}
```

### 6.2 SummaryLLMProvider（Prompt + JSON mode）

```python
from jinja2 import Environment, FileSystemLoader
from tenacity import retry, stop_after_attempt, wait_exponential

class SummaryLLMProvider:
    def __init__(self, llm_client, config):
        self.llm_client = llm_client
        self.config = config
        self.env = Environment(loader=FileSystemLoader("app/prompts"))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def summarize_full(self, content: str) -> str:
        prompt = self.env.get_template("full_summary.j2").render(
            content=content,
            min_chars=self.config.full_summary_chars[0],
            max_chars=self.config.full_summary_chars[1],
        )
        resp = self.llm_client.complete(self._build_request(prompt))
        return self._parse_json(resp.content)["summary"]

    def summarize_section(self, title: str, content: str) -> str:
        prompt = self.env.get_template("section_summary.j2").render(
            section_title=title, content=content,
            min_chars=self.config.section_summary_chars[0],
            max_chars=self.config.section_summary_chars[1],
        )
        resp = self.llm_client.complete(self._build_request(prompt))
        return self._parse_json(resp.content)["summary"]

    def _build_request(self, prompt: str):
        return LLMRequest(
            messages=[Message(role="user", content=prompt)],
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            response_format={"type": "json_object"},
        )

    def _parse_json(self, raw: str) -> dict:
        import json
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise SummaryParseError("LLM 输出非合法 JSON")
```

### 6.3 MapReduce 长文档摘要

```python
import tiktoken

class MapReduceSummarizer:
    def __init__(self, llm_provider, config):
        self.llm_provider = llm_provider
        self.config = config
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def summarize(self, text: str) -> str:
        chunks = self._split_chunks(text)
        if len(chunks) <= 1:
            return self.llm_provider.summarize_full(text)
        partials = [self.llm_provider.summarize_chunk(c) for c in chunks]
        merged = "\n\n".join(partials)
        return self.llm_provider.summarize_full(merged)

    def _split_chunks(self, text: str) -> list[str]:
        limit = self.config.map_reduce.chunk_token_limit
        overlap = self.config.map_reduce.overlap_tokens
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= limit:
            return [text]
        chunks, step = [], limit - overlap
        for i in range(0, len(tokens), step):
            chunk_tokens = tokens[i:i + limit]
            chunks.append(self.tokenizer.decode(chunk_tokens))
            if i + limit >= len(tokens):
                break
        return chunks
```

### 6.4 章节划分

```python
class SectionSplitter:
    def split_pdf(self, parsed: dict) -> list[SectionSummary]:
        toc = parsed.get("toc", [])
        pages = parsed["pages"]
        if not toc:
            return []  # 无 TOC，由上层降级为全文摘要
        sections = []
        for i, entry in enumerate(toc):
            start = entry["page"]
            end = toc[i + 1]["page"] - 1 if i + 1 < len(toc) else len(pages)
            content = "\n".join(p["text"] for p in pages[start - 1:end])
            sections.append(SectionSummary(
                title=entry["title"], summary="",
                page_range=[start, end],  # 占位，summary 由 LLM 填充
            ).model_copy(update={"_content": content}))
        return sections

    def split_audio(self, srt_segments: list[dict], chunk_minutes: int = 5) -> list[SectionSummary]:
        if not srt_segments:
            return []
        sections, bucket = [], []
        bucket_start = srt_segments[0]["start"]
        for seg in srt_segments:
            bucket.append(seg)
            if seg["end"] - bucket_start >= chunk_minutes * 60:
                sections.append(self._build_audio_section(bucket))
                bucket = []
        if bucket:
            sections.append(self._build_audio_section(bucket))
        return sections

    def _build_audio_section(self, segs: list[dict]) -> SectionSummary:
        return SectionSummary(
            title=f"{self._fmt(segs[0]['start'])}-{self._fmt(segs[-1]['end'])}",
            summary="",
            timestamp_range=[segs[0]["start"], segs[-1]["end"]],
            # 原始文本暂存于上下文，由 Service 传入 LLM
        )
```

### 6.5 SummaryService 编排

```python
class SummaryService:
    def __init__(self, llm_provider, summarizer, splitter, repo, config):
        self.llm_provider = llm_provider
        self.summarizer = summarizer
        self.splitter = splitter
        self.repo = repo
        self.config = config

    def generate(self, resource_id: str, source_type: str,
                 types: list[str]) -> SummaryResult:
        parsed = self._load_parsed(resource_id, source_type)
        result = SummaryResult(resource_id=resource_id, model=self.config.llm.model,
                               created_at=datetime.utcnow())
        try:
            if "full" in types:
                result.full_summary = self._safe_full(parsed.full_text)
            if "section" in types:
                result.sections = self._safe_sections(parsed, source_type)
        except SummaryGenerationError:
            if self.config.fallback.on_section_split_fail == "full_only" and not result.full_summary:
                result.full_summary = self._fallback_text(parsed.full_text)
                result.fallback = True
        self.repo.save(resource_id, result)
        return result

    def _safe_full(self, text: str) -> str:
        summary = self.summarizer.summarize(text)
        if not summary or not summary.strip():
            return self._fallback_text(text)
        return summary

    def _safe_sections(self, parsed, source_type: str) -> list[SectionSummary]:
        sections = (self.splitter.split_pdf(parsed.raw)
                    if source_type == "pdf"
                    else self.splitter.split_audio(parsed.srt_segments))
        filled = []
        for sec in sections:
            sec.summary = self.llm_provider.summarize_section(sec.title, sec_content)
            filled.append(sec)
        return filled

    def _fallback_text(self, text: str) -> str:
        return text[:self.config.fallback.empty_summary_chars]
```

### 6.6 Celery 任务与持久化

```python
@app.task(bind=True, base=BaseAITask)
def run_summarize(self, resource_id: str, payload: dict):
    report_status(resource_id, "running")
    try:
        result = summary_service.generate(resource_id, **payload)
        report_status(resource_id, "completed")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


class SummaryRepository:
    def save(self, resource_id: str, result: SummaryResult) -> None:
        # 全文摘要 JSON 上传 MinIO
        self.minio.upload(f"{resource_id}/summary.json", result.model_dump_json())
        # 元数据写入 summaries 表（经 Gateway 内部接口）
        records = self._to_records(result)
        self.http.post(
            f"/api/v1/internal/resources/{resource_id}/summaries",
            json=records, headers={"X-Internal-Key": self.internal_key},
        )

    def get(self, resource_id: str) -> SummaryResult | None:
        obj = self.minio.get(f"{resource_id}/summary.json")
        return SummaryResult.model_validate_json(obj) if obj else None
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 内部 Key 校验失败 | 401 | INTERNAL_AUTH_FAILED | 内部调用未授权 |
| Gateway JWT 缺失/失效 | 401 | UNAUTHORIZED | 未登录或登录已过期 |
| 资源不存在或无权访问 | 404 | RESOURCE_NOT_FOUND | 资源不存在 |
| 摘要任务进行中重复触发 | 409 | SUMMARY_IN_PROGRESS | 摘要生成中，请勿重复触发 |
| LLM 输出非 JSON | 422 | SUMMARY_PARSE_FAILED | 摘要结果解析失败 |
| LLM 调用失败（重试耗尽） | 500 | SUMMARY_GENERATION_FAILED | 摘要生成失败 |
| 摘要为空（已兜底） | 200 | - | 正常返回，`fallback=true` |
| LLM 超时 | 504 | LLM_TIMEOUT | LLM 调用超时 |

---

## 8. Web 端适配要点

- Web 端通过 `GET /api/v1/resources/{id}/summary` 获取摘要，资源卡片展示全文摘要片段（配合 S4-3 标签）
- 内容查看页按章节折叠展示章节摘要，PDF 点击跳转页码、音频点击跳转时间戳
- 摘要未就绪（任务进行中）展示「生成中」占位，前端可轮询或订阅任务状态
- `fallback=true` 时标注「自动摘要」，提示用户摘要为兜底文本
- 摘要生成失败时展示原文前若干字并提示稍后重试

---

## 9. 测试策略

- **单元测试**：map-reduce 分块、章节划分（PDF TOC / 音频 SRT）、Jinja2 模板渲染、JSON 解析、空摘要兜底、重试逻辑
- **集成测试**：触发接口 -> Celery 任务 -> mock LLM -> 持久化 -> Gateway 查询返回
- **Mock 策略**：mock `LLMClient.complete` 返回固定 JSON，验证 Prompt 构建与解析；CI 使用 mock provider 不调用真实 LLM
- **E2E 测试**：上传 PDF/音频 -> 转录/解析完成 -> 自动触发摘要 -> 前端查询展示

---

## 10. 检查清单

- [ ] 全文摘要生成（200-300 字）
- [ ] 章节摘要生成（PDF TOC + 音频 SRT 时间段）
- [ ] 长文档 map-reduce 分块汇总
- [ ] Jinja2 Prompt 模板渲染
- [ ] JSON mode 结构化输出与解析
- [ ] `summaries` 表持久化（MinIO + Gateway 内部接口）
- [ ] 内部触发接口 `POST /ai/v1/resources/{id}/summarize`
- [ ] Gateway 查询接口 `GET /api/v1/resources/{id}/summary`
- [ ] tenacity 重试 3 次（指数退避）
- [ ] 超长文档分段
- [ ] 空摘要兜底
- [ ] 权限校验（X-Internal-Key / Bearer JWT + 资源归属）
- [ ] Celery 异步触发，不阻塞主流程
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
