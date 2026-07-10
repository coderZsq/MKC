# PRD：[S3-2] 集成 text-embedding-v3 生成 Embedding

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S0-8_python_ai_service_skeleton.md](./PRD_S0-8_python_ai_service_skeleton.md)、[PRD_S3-1_text_chunking.md](./PRD_S3-1_text_chunking.md)、[PRD_S3-3_milvus_vector_store.md](./PRD_S3-3_milvus_vector_store.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-2 |
| **任务名称** | 集成 text-embedding-v3 生成 Embedding |
| **所属史诗** | E6 知识库检索 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S0-8 Python AI Service 骨架 |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为开发者，我希望 AI Service 能够调用智谱 text-embedding-v3 模型为文本分块生成稠密向量，以便写入 Milvus 向量数据库并支持后续语义检索。本任务封装 Embedding 客户端，支持批量调用、错误处理、维度校验与本地缓存，并为同 Sprint 的 S3-3 和 S3-4 提供标准化向量输出。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供 `EmbeddingService` 统一接口，输入文本列表输出向量列表
- [ ] **AC-2** 集成智谱 text-embedding-v3，输出向量维度为 2048（或官方指定维度），支持配置化模型名
- [ ] **AC-3** 支持批量调用，单批次最大文本数可配置（默认 64），超过则自动拆分
- [ ] **AC-4** 对空字符串、超长文本进行截断或过滤，避免 API 报错
- [ ] **AC-5** API 调用失败时返回明确错误码，支持指数退避重试（最多 3 次）
- [ ] **AC-6** 向量结果与原始文本顺序一致，并保留 Chunk ID 与资源 ID 映射
- [ ] **AC-7** 智谱 API Key 通过环境变量注入，不硬编码
- [ ] **AC-8** 单元/集成测试覆盖率 80%+，使用 mock 或 stub 验证批量与重试逻辑

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── services/
│   │   ├── embedding_service.py      # 统一入口
│   │   └── providers/
│   │       └── zhipu_embedding_provider.py  # 智谱客户端封装
│   └── models/
│       └── embedding.py              # Embedding 数据模型
├── config/
│   └── ai.yaml                       # embedding 配置段
└── tests/
    ├── unit/test_embedding_service.py
    └── integration/test_embedding_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| zhipuai | 2.x | 智谱官方 SDK |
| openai | 1.30+ | 兼容 OpenAI 协议的备选客户端（如 Kimi） |
| pydantic | 2.x | 模型校验 |
| tenacity | 8.x | 重试策略 |
| numpy | 1.26.x | 向量归一化与数组处理 |

---

## 技术要点

### 配置示例

```yaml
embedding:
  provider: zhipuai                      # zhipuai / openai
  model: embedding-3                     # 智谱 text-embedding-v3
  api_key: "${ZHIPU_API_KEY}"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  batch_size: 64
  max_retries: 3
  timeout: 30
  dimensions: 2048
  normalize: true
```

### 接口签名

```python
class EmbeddingService:
    async def embed(self, chunks: list[Chunk]) -> list[Embedding]:
        ...

class Embedding(BaseModel):
    chunk_id: str
    resource_id: str
    vector: list[float]
    model: str
    dimensions: int
```

### 批量处理流程

1. 接收 Chunk 列表，校验文本非空
2. 按 `batch_size` 分组，超出长度文本截断
3. 调用智谱 Embedding API
4. 归一化向量（可选）
5. 按输入顺序组装 Embedding 结果
6. 失败批次重试，全部失败时抛异常

### 错误处理与降级策略

- API Key 缺失：启动时校验，缺失则服务无法启动
- 单批次失败：重试 3 次；全部失败则标记任务失败
- 智谱服务不可用：可切换至 OpenAI 兼容备选 provider（配置化）
- 向量维度不一致：返回 500 并记录错误，不写入 Milvus

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 智谱 API 调用延迟高 | 批量分块处理慢 | 控制 batch_size，失败时重试 |
| 免费额度不足 | 测试阶段 token 受限 | 提供本地 mock provider，CI 使用 stub |
| 向量维度变更 | 下游 Milvus schema 不兼容 | 配置化 dimensions，启动时校验 |

---

## Web 端适配

本任务为后端 AI Service 能力，Web 端不直接调用。Embedding 向量不暴露给客户端，仅用于内部检索。

---

## 备注

- 建议预留 `provider` 接口，便于后续接入 Kimi、OpenAI 等兼容服务
-  Embedding 结果应存储在内存或临时队列，由 S3-3 批量写入 Milvus
- 本地开发可用固定随机向量 provider 避免调用远程 API
