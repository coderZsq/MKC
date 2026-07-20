# PRD：[S6-2] 引入 LlamaIndex 依赖与配置开关

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 关联文档：[PRD_S6-1_rag_migration_boundary.md](./PRD_S6-1_rag_migration_boundary.md)、[TECH_S6-1_rag_migration_boundary.md](../tech/TECH_S6-1_rag_migration_boundary.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S6-2 |
| **任务名称** | 引入 LlamaIndex 依赖与配置开关 |
| **所属史诗** | E13 RAG 内核升级 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S6-1 |
| **目标 Sprint** | Sprint 6 |

---

## 描述

作为开发者，我希望安全引入 LlamaIndex 相关依赖，并增加 `RAG_ENGINE=legacy/llamaindex` 配置开关，以便后续任务可以在不影响默认问答链路的情况下逐步接入 LlamaIndex。默认行为必须保持 legacy。

---

## 验收标准（AC）

- [ ] **AC-1** `ai-service/requirements*.txt` 或项目依赖文件声明 LlamaIndex 核心依赖，并固定可复现版本范围
- [ ] **AC-2** 新增 `RAG_ENGINE` 配置，合法值为 `legacy`、`llamaindex`，默认 `legacy`
- [ ] **AC-3** 配置解析支持环境变量覆盖，并对非法值返回清晰配置错误
- [ ] **AC-4** 增加 runtime capability 检查：缺少 LlamaIndex 依赖时 legacy 仍可启动
- [ ] **AC-5** 测试覆盖默认值、环境变量覆盖、非法配置、依赖缺失降级
- [ ] **AC-6** 静态检查和测试覆盖率 80%+

---

## 推荐目录结构

```text
ai-service/
├── app/
│   ├── core/config.py
│   └── services/rag_engine/
│       ├── __init__.py
│       └── config.py
├── requirements.txt
├── requirements-dev.txt
└── tests/services/rag_engine/test_config.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| llama-index-core | 0.10+ / 0.11+ | LlamaIndex 核心抽象 |
| llama-index-vector-stores-milvus | 与 core 兼容 | 后续 Milvus 适配 |
| pydantic-settings | 2.x | 配置解析 |

---

## 技术要点

- 依赖引入必须尽量懒加载，避免 legacy 模式因为 LlamaIndex 可选组件问题无法启动。
- `RAG_ENGINE` 只控制 AI Service 内部检索引擎，不改变 Gateway 或 Flutter 配置。
- 非法配置应在服务启动阶段暴露，避免运行中才静默回退。
- CI 应在无外部 LLM Key 的情况下完成配置测试。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LlamaIndex 依赖体积较大 | CI 安装变慢 | 固定最小必要包，避免一次性引入 reader/agent 全家桶 |
| Milvus 插件版本不兼容 | 后续 S6-4 阻塞 | S6-2 只声明核心，S6-4 再验证插件 |
| 默认开关误切换 | 线上行为变化 | 默认 legacy，并增加测试锁定 |

---

## Web 端适配

本任务不涉及 Web 端特殊适配。

---

## 备注

- S6-2 不实现 LlamaIndex 查询逻辑，只建立依赖和配置地基。
- 后续 S6-6 负责真正将 QA Service 接入双引擎。
