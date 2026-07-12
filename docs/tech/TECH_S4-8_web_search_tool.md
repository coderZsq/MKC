# 技术文档：[S4-8] 接入 Web Search 工具（可选）

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联 PRD：[../prd/PRD_S4-8_web_search_tool.md](../prd/PRD_S4-8_web_search_tool.md)
> 级别：AI 工程师

---

## 1. 文档目标

定义 AI Service 中 Web Search 工具的技术实现：Serper / Bing provider 抽象、`web_search` 工具签名、LangGraph 工具节点接入、结果解析与 LLM 摘要、限流/超时/重试、失败降级、来源区分与测试策略，作为 S4-4 Agent 工作流的可选外部信息补充能力。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- httpx 0.27.x（异步 HTTP 调用搜索 API）
- langgraph 0.x（Agent 工作流工具节点）
- langchain-core 0.x（`@tool` 装饰器）
- tenacity 8.x（重试策略）
- pydantic 2.x（模型校验）
- zhipuai 2.x（GLM-4 摘要搜索结果）

---

## 3. 接口契约

### 3.1 工具接口（Agent 内部调用）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 工具调用 | `web_search(query, top_k)` | Agent 内部 | LangGraph 工具节点，无 HTTP |
| POST | `/ai/v1/tools/web-search` | Internal API Key | 手工测试端点（`X-Internal-Key`） |

### 3.2 请求示例

```json
POST /ai/v1/tools/web-search
Headers: X-Internal-Key: <key>
{
  "query": "2026 年大模型推理优化最新进展",
  "top_k": 5
}
```

### 3.3 响应示例

```json
{
  "results": [
    {
      "title": "大模型推理加速技术综述",
      "url": "https://example.com/llm-inference",
      "snippet": "本文总结了 KV Cache、量化与投机解码等推理优化方向..."
    }
  ],
  "source_type": "web",
  "fallback": false
}
```

### 3.4 错误码

| HTTP 状态 | Error Code | Message | 说明 |
|---|---|---|---|
| 401 | WEB_SEARCH_AUTH_FAILED | 内部 Key 校验失败 | 测试端点认证失败 |
| 422 | WEB_SEARCH_INVALID_INPUT | 查询参数非法 | query 为空或 top_k 超限 |
| 504 | WEB_SEARCH_TIMEOUT | 搜索调用超时 | 已降级返回空结果 |
| 503 | WEB_SEARCH_UNAVAILABLE | 搜索服务不可用 | 重试后仍失败，降级空结果 |

> 注：生产链路为 Agent 内部工具调用，失败时返回空 `WebSearchResponse`（`fallback=true`），不向 Agent 抛 HTTP 错误。

---

## 4. 配置

新增 `config/ai.yaml` 的 `web_search` 配置段：

```yaml
web_search:
  provider: serper                    # serper / bing / mock
  serper:
    api_key: "${SERPER_API_KEY}"
    base_url: "https://google.serper.dev"
    timeout: 10
  bing:
    api_key: "${BING_API_KEY}"
    base_url: "https://api.bing.microsoft.com/v7.0/search"
    timeout: 10
  top_k: 5                            # 默认结果数
  max_top_k: 10                       # 结果数上限
  rate_limit_per_minute: 20           # 限流阈值
  max_retries: 2                      # 重试次数
  retry_backoff_min: 1
  retry_backoff_max: 5
  snippet_max_length: 200             # snippet 截断长度
```

---

## 5. 模块设计

### 5.1 WebSearchTool（LangGraph 工具节点）

```python
from langchain_core.tools import tool

class WebSearchTool:
    def __init__(self, provider: BaseSearchProvider, config: WebSearchConfig):
        self._provider = provider
        self._config = config

    @tool
    async def web_search(self, query: str, top_k: int = 5) -> WebSearchResponse:
        """当知识库检索不足时调用，返回外部网络搜索结果。
        Args:
            query: 搜索查询词
            top_k: 返回结果数量，默认 5，上限 10
        Returns:
            WebSearchResponse: 含 results 列表与 source_type=web
        """
        ...
```

### 5.2 BaseSearchProvider（抽象 provider）

```python
class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]: ...

    @abstractmethod
    def _parse_response(self, raw: dict) -> list[WebSearchResult]: ...
```

### 5.3 SerperProvider

```python
class SerperProvider(BaseSearchProvider):
    def __init__(self, config: SerperConfig):
        self._client = httpx.AsyncClient(timeout=config.timeout)
        self._api_key = config.api_key
        self._base_url = config.base_url

    async def search(self, request: WebSearchRequest) -> list[WebSearchResult]:
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        payload = {"q": request.query, "num": request.top_k}
        response = await self._client.post(self._base_url, json=payload, headers=headers)
        response.raise_for_status()
        return self._parse_response(response.json())
```

### 5.4 BingProvider

- 使用 `Ocp-Apim-Subscription-Key` 头携带 `BING_API_KEY`
- 解析 `webPages.value` 数组，映射 `name`/`url`/`snippet`

### 5.5 数据模型

```python
class WebSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    top_k: int = Field(default=5, ge=1, le=10)

class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class WebSearchResponse(BaseModel):
    results: list[WebSearchResult]
    source_type: Literal["web"] = "web"
    fallback: bool = False
```

---

## 6. 关键代码实现

### 6.1 工具调用（含限流、重试、降级）

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class WebSearchTool:
    @tool
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def web_search(self, query: str, top_k: int = 5) -> WebSearchResponse:
        # 输入校验
        request = WebSearchRequest(query=query, top_k=min(top_k, self._config.max_top_k))
        try:
            self._rate_limiter.acquire()  # 令牌桶限流
            results = await self._provider.search(request)
            return WebSearchResponse(results=results)
        except Exception as exc:
            logger.warning("web_search fallback: %s", exc)
            return WebSearchResponse(results=[], fallback=True)
```

### 6.2 结果解析（Serper）

```python
def _parse_response(self, raw: dict) -> list[WebSearchResult]:
    results: list[WebSearchResult] = []
    for item in raw.get("organic", [])[: self._max_top_k]:
        snippet = (item.get("snippet") or "")[: self._snippet_max_length]
        results.append(WebSearchResult(
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=snippet,
        ))
    return results
```

### 6.3 LangGraph 工具节点接入

```python
from langgraph.prebuilt import ToolNode

def build_web_search_node(tool: WebSearchTool) -> ToolNode:
    """注册为 LangGraph 工具节点，由 Agent 自主决定是否调用。"""
    return ToolNode([tool.web_search])
```

### 6.4 摘要纳入上下文（来源区分）

```python
async def summarize_and_inject(results: list[WebSearchResult], llm: LLMClient) -> str:
    """将搜索结果经 GLM-4 摘要后，标注「网络来源」注入上下文。"""
    if not results:
        return ""
    joined = "\n".join(f"- {r.title}: {r.snippet} ({r.url})" for r in results)
    prompt = f"请将以下网络搜索结果摘要为简洁信息，标注为「网络来源」：\n{joined}"
    summary = await llm.complete(LLMRequest(messages=[Message(role="user", content=prompt)]))
    return f"【网络来源】{summary.content}"
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message | 处理 |
|---|---|---|---|---|
| API Key 缺失 | - | - | 启动报错 | 拒绝启动 |
| API Key 无效 | 503 | WEB_SEARCH_UNAVAILABLE | 搜索服务不可用 | 降级返回空 |
| 查询参数非法 | 422 | WEB_SEARCH_INVALID_INPUT | 查询参数非法 | 测试端点返回 422 |
| 超时 | 504 | WEB_SEARCH_TIMEOUT | 搜索调用超时 | 降级返回空，fallback=true |
| 限流（429） | 503 | WEB_SEARCH_UNAVAILABLE | 搜索服务不可用 | 退避重试后降级 |
| 内部 Key 缺失 | 401 | WEB_SEARCH_AUTH_FAILED | 内部 Key 校验失败 | 测试端点返回 401 |
| 解析异常 | - | - | - | 跳过异常条目，返回有效结果 |

---

## 8. Web 端适配要点

- Web Search 工具为 AI Service 内部能力，Web 端不直接调用搜索 API
- 搜索结果经 LLM 摘要后通过 S3-6 SSE 问答链路下发，Web 端在答案中可见「网络来源」标注
- web 内容不进入 S4-5 引用溯源的 `citation` 事件，仅文档来源参与引用
- 测试端点 `POST /ai/v1/tools/web-search` 仅供后端联调，不暴露给 Gateway / Web 端

---

## 9. 测试策略

- **单元测试**：provider 选择、请求构建、响应解析、限流、重试、降级逻辑、输入校验
- **集成测试**：mock provider 验证 LangGraph 工具节点调用与上下文注入
- **Mock 策略**：`MockSearchProvider` 返回固定结果列表，CI 不调用真实搜索 API
- **覆盖率**：目标 80%+，覆盖正常调用、超时、限流、降级、来源区分

---

## 10. 检查清单

- [ ] `web_search(query, top_k)` 工具接口
- [ ] Serper / Bing provider 可配置切换
- [ ] `@tool` 装饰器 + LangGraph 工具节点接入
- [ ] 搜索结果 LLM 摘要 + 上下文注入
- [ ] 限流、超时、重试
- [ ] 失败降级返回空，不阻塞 Agent
- [ ] 来源区分（web 不作为文档引用）
- [ ] API Key 环境变量注入，启动校验
- [ ] `POST /ai/v1/tools/web-search` 测试端点（`X-Internal-Key`）
- [ ] 测试覆盖率 80%+
- [ ] ruff / mypy 通过
- [ ] 无硬编码密钥
