# 技术文档：[S6-2] 引入 LlamaIndex 依赖与配置开关

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-2_llamaindex_dependency_config.md](../prd/PRD_S6-2_llamaindex_dependency_config.md)

---

## 1. 文档目标

定义 LlamaIndex 依赖引入方式、`RAG_ENGINE` 配置契约、非法配置处理和 legacy 默认行为。

---

## 2. 技术栈

- Python 3.11+
- pydantic / pydantic-settings
- LlamaIndex core
- pytest

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 配置 | `RAG_ENGINE` | 环境变量 | 选择 `legacy` 或 `llamaindex` |

不新增 HTTP API。

---

## 4. 配置

```python
class RagEngineConfig(BaseModel):
    engine: Literal["legacy", "llamaindex"] = "legacy"
    llamaindex_enabled: bool = False

    @classmethod
    def from_env(cls) -> "RagEngineConfig":
        engine = os.getenv("RAG_ENGINE", "legacy").strip().lower()
        return cls(engine=engine, llamaindex_enabled=engine == "llamaindex")
```

`.env.example` 增加：

```bash
RAG_ENGINE=legacy
```

---

## 5. 模块设计

- `app/services/rag_engine/config.py`：解析和校验 RAG 引擎配置。
- `app/core/config.py`：暴露 `rag_engine` 配置段。
- `requirements.txt`：增加最小 LlamaIndex 依赖。
- `tests/services/rag_engine/test_config.py`：覆盖默认值和非法配置。

---

## 6. 关键代码实现

```python
def require_llamaindex() -> None:
    try:
        import llama_index.core  # noqa: F401
    except ImportError as exc:
        raise RagEngineUnavailableError("LlamaIndex 依赖未安装") from exc
```

legacy 模式不得调用 `require_llamaindex()`。

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 非法配置值 | N/A | RAG_ENGINE_INVALID | RAG_ENGINE 仅支持 legacy/llamaindex |
| 依赖缺失 | 503 | RAG_ENGINE_UNAVAILABLE | LlamaIndex 依赖未安装 |

---

## 8. Web 端适配要点

无需 Web 端改动。

---

## 9. 测试策略

- 单元测试：默认 legacy、环境变量覆盖、非法值。
- 兼容测试：legacy 模式下未安装 LlamaIndex 时服务配置仍可构建。
- 静态检查：ruff、mypy。

---

## 10. 检查清单

- [ ] 依赖已声明
- [ ] `RAG_ENGINE` 已配置
- [ ] 默认 legacy
- [ ] 非法配置有错误
- [ ] 测试覆盖率 80%+
