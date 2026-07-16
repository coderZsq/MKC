# 技术文档：[S5-5] 接入 LangSmith / Langfuse

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S5-5_langsmith_langfuse_observability.md](../prd/PRD_S5-5_langsmith_langfuse_observability.md)

---

## 1. 文档目标

定义 LLM 观测 provider 抽象、LangSmith/Langfuse 接入方式、配置开关、脱敏策略与降级行为。

---

## 2. 技术栈

- Python 3.11+
- zhipuai / Kimi SDK
- langfuse 2.x
- langsmith 0.x
- pydantic 2.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| SDK | `LLMObserver.record_generation()` | 环境变量 | 记录 LLM 调用 |
| SDK | `LLMObserver.record_error()` | 环境变量 | 记录失败 |

事件模型：

```json
{
  "trace_id": "abc",
  "prompt_version": "qa_v3",
  "provider": "zhipu",
  "model": "glm-4",
  "latency_ms": 1820,
  "input_tokens": 1200,
  "output_tokens": 320,
  "status": "success"
}
```

---

## 4. 配置

```yaml
llm_observability:
  provider: none
  redact: true
  max_prompt_chars: 2000
  max_completion_chars: 2000
```

环境变量：

```text
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=
```

---

## 5. 模块设计

- `LLMObserver`：抽象接口。
- `NoopObserver`：默认实现。
- `LangfuseObserver`：写入 Langfuse trace/generation。
- `LangSmithObserver`：写入 LangSmith run。
- `Redactor`：统一脱敏、截断 prompt 和 completion。

---

## 6. 关键代码实现

```python
class LLMObserver(Protocol):
    async def record_generation(self, event: LLMGenerationEvent) -> None: ...
    async def record_error(self, event: LLMErrorEvent) -> None: ...

async def safe_record(observer: LLMObserver, event: LLMGenerationEvent) -> None:
    try:
        await observer.record_generation(event)
    except Exception as exc:
        logger.warning("llm observer fallback: %s", exc)
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| provider 配置缺失 | N/A | LLM_OBSERVER_CONFIG_MISSING | LLM 观测配置缺失，已降级 |
| 远端写入失败 | N/A | LLM_OBSERVER_EXPORT_FAILED | LLM 观测写入失败 |
| 脱敏失败 | N/A | LLM_OBSERVER_REDACT_FAILED | LLM 观测脱敏失败 |

---

## 8. Web 端适配要点

Web 端无需改动。错误反馈可包含后端返回的 trace_id。

---

## 9. 测试策略

- 单元测试：provider factory、noop 降级、脱敏截断。
- 集成测试：mock Langfuse/LangSmith client 写入事件。
- 安全测试：日志和事件中无密钥、JWT、原始文件正文。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] 测试覆盖率 80%+
- [ ] 配置文档同步更新
