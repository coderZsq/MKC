# PRD：[S4-2] 实现标签/实体抽取

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S2-3_audio_text_cleaning.md](./PRD_S2-3_audio_text_cleaning.md)、[PRD_S2-4_pdf_text_extraction.md](./PRD_S2-4_pdf_text_extraction.md)、[PRD_S3-5_glm4_kimi_llm.md](./PRD_S3-5_glm4_kimi_llm.md)、[PRD_S4-3_resource_card_summary_tag.md](./PRD_S4-3_resource_card_summary_tag.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-2 |
| **任务名称** | 实现标签/实体抽取 |
| **所属史诗** | E8 智能抽取 |
| **故事点** | 3 |
| **优先级** | Should |
| **依赖** | S2-3 音频文本清洗、S2-4 PDF 文本提取、S3-5 智谱 GLM-4 / Kimi LLM |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为用户，我希望资源（音频转录文本、PDF 提取文本）处理完成后，系统自动抽取关键词标签与命名实体，以便在资源卡片上快速浏览核心信息、在检索时按标签与实体进行过滤。本任务在 AI Service 中实现异步标签/实体抽取服务，使用 LLM JSON mode 输出结构化结果，并对标签进行去重与归一化，最终持久化到 `resource_tags` 与 `resource_entities` 表，供 S4-3 资源卡片展示与后续检索过滤使用。

---

## 验收标准（AC）

- [ ] **AC-1** 资源处理完成后由 Celery 异步触发标签/实体抽取任务，不阻塞主流程
- [ ] **AC-2** LLM 抽取 5-10 个关键词标签，数量超出时截断、不足时保留实际结果
- [ ] **AC-3** LLM 抽取命名实体（NER），类型覆盖 PERSON/ORG/DATE/LOC/GPE/MISC，每条实体带原文 mention 与归一化值
- [ ] **AC-4** 标签去重、归一化（小写、同义词合并），限制最终数量为 5-10
- [ ] **AC-5** LLM 以 JSON mode 输出结构化结果，字段固定为 `tags` 与 `entities`
- [ ] **AC-6** 抽取结果存储到 `resource_tags(resource_id, tag, source)` 与 `resource_entities(resource_id, entity, type, mention)`
- [ ] **AC-7** 内部接口 `POST /ai/v1/resources/{resource_id}/extract-tags`（X-Internal-Key）；Gateway `GET /api/v1/resources/{id}/tags`（Bearer JWT）
- [ ] **AC-8** LLM 输出非法 JSON 时重试（3 次指数退避）并降级为正则/规则抽取；资源内容为空时返回空结果兜底
- [ ] **AC-9** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── api/
│   │   └── extraction.py              # 抽取接口（内部 + Gateway）
│   ├── services/
│   │   ├── extraction_service.py      # 抽取 orchestration
│   │   ├── tag_normalizer.py          # 标签去重与归一化
│   │   └── entity_resolver.py         # 实体归一化
│   ├── providers/
│   │   ├── base_extraction_provider.py
│   │   ├── llm_extraction_provider.py # LLM JSON mode 抽取
│   │   └── rule_extraction_provider.py# 正则/规则降级抽取
│   ├── repositories/
│   │   ├── tag_repository.py          # resource_tags 仓储
│   │   └── entity_repository.py       # resource_entities 仓储
│   ├── models/
│   │   ├── tag.py                     # Tag 数据模型
│   │   ├── entity.py                  # Entity 数据模型
│   │   └── extraction.py              # 请求/响应模型
│   └── tasks/
│       └── extract_tags_task.py       # Celery 异步任务
└── tests/
    ├── unit/test_tag_normalizer.py
    ├── unit/test_entity_resolver.py
    ├── unit/test_llm_extraction_provider.py
    ├── unit/test_rule_extraction_provider.py
    └── integration/test_extraction_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| 智谱 GLM-4 / Kimi API | - | LLM JSON mode 抽取标签与实体 |
| zhipuai | 2.x | 智谱 GLM-4 SDK |
| openai | 1.30+ | Kimi / OpenAI 兼容协议 |
| tenacity | 8.x | 重试策略 |
| pydantic | 2.x | 数据模型校验 |
| Celery | 5.4.x | 异步任务调度 |
| MySQL | - | 标签与实体持久化 |
| 正则表达式 | - | 规则降级抽取 |

---

## 技术要点

### LLM JSON mode 输出示例

```json
{
  "tags": ["机器学习", "模型训练", "数据集", "神经网络", "深度学习", "GPU", "张三", "算法", "参数调优", "过拟合"],
  "entities": [
    {"text": "张三", "type": "PERSON", "mention": "张三"},
    {"text": "OpenAI", "type": "ORG", "mention": "OpenAI"},
    {"text": "2026年7月", "type": "DATE", "mention": "2026年7月"},
    {"text": "北京", "type": "GPE", "mention": "北京"},
    {"text": " transformers 库", "type": "MISC", "mention": "transformers"}
  ]
}
```

### 内部接口请求示例

```json
POST /ai/v1/resources/{resource_id}/extract-tags
Headers: X-Internal-Key: <key>
{
  "content": "本次会议由张三主持，讨论了机器学习模型训练的数据集选取……",
  "source_type": "audio"
}
```

### 内部接口响应示例

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

### Gateway 接口响应示例

```json
GET /api/v1/resources/{id}/tags
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

### 数据流

1. 资源处理（ASR 清洗 / PDF 提取）完成，写入 task.result
2. Celery 异步触发 `extract_tags_task`，传入 resource_id 与内容
3. 调用 `LLMExtractionProvider`，以 JSON mode 请求 LLM
4. 解析 JSON，校验字段与类型
5. `TagNormalizer` 去重、小写、同义词合并、截断至 5-10 个
6. `EntityResolver` 归一化实体值（去除首尾空白、统一大小写）
7. 通过 `TagRepository` / `EntityRepository` 持久化到 MySQL
8. 返回结构化结果，标记 `source`（llm/rule）与 `fallback` 标志

### 错误处理与降级策略

- **资源内容为空**：跳过抽取，返回空 tags 与 entities，标记 `fallback: true`
- **LLM 返回非法 JSON**：重试 3 次（指数退避 2/4/8 秒），仍失败则降级为 `RuleExtractionProvider` 正则抽取
- **LLM 调用超时**：超时 60s 后降级为规则抽取
- **LLM 返回实体类型非法**：过滤非法类型，仅保留 PERSON/ORG/DATE/LOC/GPE/MISC
- **数据库写入失败**：记录错误日志，任务标记 failed，不影响已有数据

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LLM 输出 JSON 不稳定 | 解析失败 | 重试 + 规则降级兜底 |
| 大文本超出 token 限制 | 截断丢失信息 | 按段落分批抽取后合并 |
| 同义词归一化覆盖不全 | 标签冗余 | 维护同义词表，后续迭代扩展 |
| 抽取延迟影响卡片展示 | 用户体验差 | 异步执行，卡片先展示已有内容，抽取完成后刷新 |

---

## Web 端适配

Web 端资源卡片通过 Gateway `GET /api/v1/resources/{id}/tags` 获取标签与实体，在 S4-3 资源卡片中以标签云与实体列表形式展示。抽取尚未完成时卡片展示骨架占位，完成后自动刷新。标签可点击触发按标签检索过滤。

---

## 备注

- 标签与实体抽取结果均保留 `source` 字段（llm / rule），便于后续质量评估
- 同义词归一化表初始内置常见映射（如 "AI" ↔ "人工智能"），可通过配置扩展
- 实体类型遵循 PERSON/ORG/DATE/LOC/GPE/MISC 标准集合，后续可按需扩展
- 抽取结果用于 S4-3 资源卡片展示与后续检索过滤，需保证字段一致性
