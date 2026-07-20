# S6-6 测试用例：将 QA Service 接入可切换 RAG Engine

## 1. 范围与目标

验证 QA Service 在 legacy 与 LlamaIndex 两种 RAG 引擎下均保持相同 SSE、citation、错误和降级契约。

## 2. 测试环境

- Python 3.11+
- pytest / pytest-asyncio
- fake legacy engine
- fake LlamaIndex engine
- mock LLMClient

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-6-001 | Functional | Unit | P0 | legacy engine 可生成 SSE | RAG_ENGINE=legacy | 调用 stream_answer | 收到 chunk/done | PRD AC-1, AC-2 |
| MKC-TC-S6-6-002 | Functional | Unit | P0 | llamaindex engine 可生成 SSE | RAG_ENGINE=llamaindex | 调用 stream_answer | 收到 chunk/done | PRD AC-1, AC-2 |
| MKC-TC-S6-6-003 | Functional | Unit | P0 | citation 格式兼容 | fake engine 返回 chunks | 收集事件 | citation 字段与 legacy 一致 | PRD AC-3 |
| MKC-TC-S6-6-004 | Functional | Unit | P1 | 无 resource_ids 时跳过检索 | 空 resource_ids | 调用 stream_answer | 直接 LLM streaming | 现有行为 |
| MKC-TC-S6-6-005 | Functional | Unit | P1 | legacy 行为回归通过 | 现有 QA tests | RAG_ENGINE=legacy 运行测试 | 测试无需大改 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-6-006 | Security | Unit | P0 | 检索越权错误转 error event | engine 抛 FORBIDDEN | stream_answer | 返回 error event，不泄露堆栈 | PRD AC-4 |
| MKC-TC-S6-6-007 | Security | Static | P1 | SSE error 不包含内部路径 | 模拟异常 | 检查事件 data | 无本地路径/stack trace | PRD AC-4 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-6-008 | Negative | Unit | P0 | llamaindex 检索失败标准错误 | engine 抛 RETRIEVAL_UNAVAILABLE | stream_answer | 返回 error event | PRD AC-4 |
| MKC-TC-S6-6-009 | Negative | Unit | P1 | LLM 失败仍按既有降级 | mock LLM timeout | stream_answer | fallback 或 error 与现有一致 | PRD AC-5 |
| MKC-TC-S6-6-010 | Negative | Unit | P1 | 空结果可完成 | engine 返回空 chunks | stream_answer | 收到 done 或可解释答案 | PRD AC-6 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-6-011 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S6-6-012 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-6-013 | Compatibility | E2E | P1 | Flutter Web legacy 聊天可用 | Web app 启动 | legacy 模式提问 | 页面显示流式答案和引用 | PRD Web 端适配 |
| MKC-TC-S6-6-014 | Compatibility | E2E | P1 | Flutter Web llamaindex 聊天可用 | Web app 启动 | llamaindex 模式提问 | 页面显示流式答案和引用 | PRD Web 端适配 |

## 4. 测试执行清单

- [ ] legacy QA tests 通过
- [ ] llamaindex QA tests 通过
- [ ] SSE 事件兼容
- [ ] citation 兼容
- [ ] Web smoke 通过
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
