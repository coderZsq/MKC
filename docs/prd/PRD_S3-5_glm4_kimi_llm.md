# PRD：[S3-5] 接入智谱 GLM-4 / Kimi 生成答案

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S0-8_python_ai_service_skeleton.md](./PRD_S0-8_python_ai_service_skeleton.md)、[PRD_S3-4_vector_retrieval_context.md](./PRD_S3-4_vector_retrieval_context.md)、[PRD_S3-6_sse_qa_api.md](./PRD_S3-6_sse_qa_api.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-5 |
| **任务名称** | 接入智谱 GLM-4 / Kimi 生成答案 |
| **所属史诗** | E7 AI 对话 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S0-8 Python AI Service 骨架 |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为用户，我希望知识库助手能够基于检索到的上下文，使用智谱 GLM-4 或 Kimi 等大模型生成自然语言答案。本任务在 AI Service 中封装统一的 LLM 客户端，支持同步生成与 Server-Sent Events（SSE）流式输出，并提供模型切换、超时控制、错误处理与成本控制机制。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供统一的 `LLMClient` 接口，支持 `complete` 与 `stream_complete` 两种调用模式
- [ ] **AC-2** 集成智谱 GLM-4（默认）与 Kimi（备选），通过配置切换 provider 和 model
- [ ] **AC-3** 流式输出以 SSE 格式逐字返回，支持 `content` 增量与 `finish_reason`
- [ ] **AC-4** 请求超时、最大 token 数、温度等参数可配置（默认超时 60s，max_tokens 2048，temperature 0.7）
- [ ] **AC-5** LLM API 调用失败时返回明确错误码，支持 3 次指数退避重试
- [ ] **AC-6** API Key 通过环境变量注入，代码中不保留任何密钥
- [ ] **AC-7** 提供 mock provider，支持 CI 与本地开发不调用真实 LLM
- [ ] **AC-8** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── services/
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py         # 统一接口
│   │   │   ├── base_provider.py      # 抽象 provider
│   │   │   ├── zhipu_provider.py     # 智谱 GLM-4
│   │   │   ├── kimi_provider.py      # Moonshot Kimi
│   │   │   └── mock_provider.py      # 本地 mock
│   │   └── models/
│   │       ├── llm_request.py
│   │       └── llm_response.py
├── config/
│   └── ai.yaml
└── tests/
    ├── unit/test_llm_client.py
    ├── unit/test_zhipu_provider.py
    └── integration/test_llm_stream.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| zhipuai | 2.x | 智谱 GLM-4 SDK |
| openai | 1.30+ | Kimi / OpenAI 兼容协议 |
| tenacity | 8.x | 重试策略 |
| pydantic | 2.x | 模型校验 |

---

## 技术要点

### 配置示例

```yaml
llm:
  provider: zhipuai                      # zhipuai / kimi / mock
  model: glm-4-flash                   # 默认模型
  api_key: "${ZHIPU_API_KEY}"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  temperature: 0.7
  max_tokens: 2048
  timeout: 60
  max_retries: 3
  stream: true
```

### 接口签名

```python
class LLMClient:
    async def complete(self, request: LLMRequest) -> LLMResponse: ...
    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]: ...

class LLMRequest(BaseModel):
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 2048

class LLMResponse(BaseModel):
    content: str
    model: str
    finish_reason: str
    usage: dict
```

### 流式输出格式

```text
id: chatcmpl-xxx
event: message
data: {"delta": {"content": "本次"}, "finish_reason": null}

event: message
data: {"delta": {"content": "会议"}, "finish_reason": null}

event: done
data: {"finish_reason": "stop"}

```

### 错误处理与降级策略

- API Key 缺失：启动时报错，拒绝启动
- 主模型失败：按配置切换至备选模型（如 GLM-4 → Kimi）
- 流式中断：返回已生成内容并标记 `finish_reason: length` 或 `error`
- 超时：返回 504，由上层重试或提示用户
- 余额不足：记录错误码，Gateway 提示用户

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LLM API 延迟或限流 | 用户体验差 | 控制并发、重试、超时 |
| 流式输出解析异常 | SSE 中断 | 提供健壮的事件解析与错误兜底 |
| 测试阶段 token 费用高 | 成本超预期 | 使用 mock provider 与免费模型 |

---

## Web 端适配

LLM 生成能力由 AI Service 提供，Web 端通过 S3-6 的 SSE 问答 API 间接消费流式输出。Web 端无需直接调用智谱或 Kimi SDK。

---

## 备注

- 建议将 `LLMClient` 设计为可扩展接口，便于 S4 引入更多模型与 Agent 节点
- 流式输出的事件格式需要与 S3-6 的 SSE 转发协议对齐
- 成本控制：记录每次调用的 token 用量，S5 可接入监控
