# PRD：[S2-3] 音频文本清洗（语气词/重复）

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[PRD_S2-1_faster_whisper_asr.md](./PRD_S2-1_faster_whisper_asr.md)、[PRD_S2-2_srt_generation.md](./PRD_S2-2_srt_generation.md)、[TECH_S2-1_faster_whisper_asr.md](../tech/TECH_S2-1_faster_whisper_asr.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-3 |
| **任务名称** | 音频文本清洗（语气词/重复） |
| **所属史诗** | E4 音频转录 |
| **故事点** | 3 |
| **优先级** | Should |
| **依赖** | S2-1 faster-whisper ASR、S2-2 SRT 生成 |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望转录后的文本去掉重复词、语气词和口吃，以获得更通顺的阅读体验。本任务在 ASR 之后增加 LLM 后处理步骤，对转录文本进行清洗并同步更新 SRT 文本内容。

---

## 验收标准（AC）

- [ ] **AC-1** 在 ASR 完成后调用文本清洗服务，输入为转录 segments
- [ ] **AC-2** 清洗规则覆盖：语气词（嗯、啊、哦）、重复词、口吃、无意义填充词
- [ ] **AC-3** 提供基于规则的快速清洗与基于 LLM 的深度清洗两种模式
- [ ] **AC-4** 清洗后保留原始时间戳，仅修改文本内容
- [ ] **AC-5** 清洗后的文本与 SRT 重新生成并存储
- [ ] **AC-6** 清洗失败时保留原始 ASR 结果，不阻塞任务完成
- [ ] **AC-7** 单元测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── services/
│   │   ├── text_cleaning_service.py    # 清洗 orchestration
│   │   ├── rule_cleaner.py             # 规则清洗
│   │   └── llm_cleaner.py              # LLM 清洗
│   ├── clients/
│   │   └── zhipu_client.py             # 智谱 GLM 调用
│   └── utils/
│       └── text_utils.py               # 文本分段
└── tests/
    └── unit/test_text_cleaning.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| 智谱 GLM-4 / Kimi API | - | LLM 深度清洗 |
| pydantic | 2.x | 数据模型校验 |
| 正则表达式 | - | 规则清洗 |

---

## 技术要点

### 规则清洗示例

```python
FILLER_WORDS = ["嗯", "啊", "哦", "呃", "那个", "就是", "然后"]
REPEAT_PATTERN = re.compile(r"(\b\w+\b)(\s+\1){2,}")  # 连续重复 2 次以上
```

### LLM 清洗 Prompt 示例

```text
你是一名语音转录校对专家。请清洗以下转录文本，删除语气词、重复词和口吃，保持原意与时间戳不变。只输出清洗后的文本，不要解释。

原始文本：
{segment_text}
```

### 数据流

1. ASR 输出 segments
2. 规则清洗（轻量、快速）
3. 按 batch 调用 LLM 深度清洗
4. 合并回 segments
5. 触发 SRT 重新生成

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| LLM 调用慢且贵 | 任务完成时间变长 | 默认使用规则清洗；LLM 清洗为可选开关 |
| LLM 改变语义 | 内容失真 | 限制温度参数，使用 few-shot 示例 |
| 清洗失败阻塞任务 | 用户体验差 | 失败时 fallback 到原始 ASR 结果 |

---

## Web 端适配

Web 端内容查看页展示清洗后的文本，并提供切换“查看原文”的入口。清洗失败时默认展示原始文本。

---

## 备注

- 本任务为 Should 优先级，排期紧张时可延后或只保留规则清洗
- 清洗结果与原始文本均需保留，供后续评估对比
- 清洗后需重新生成 SRT，保持字幕与文本一致
