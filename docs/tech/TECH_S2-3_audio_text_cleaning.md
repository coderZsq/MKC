# 技术文档：[S2-3] 音频文本清洗（语气词/重复）

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S2-3_audio_text_cleaning.md](../prd/PRD_S2-3_audio_text_cleaning.md)

---

## 1. 文档目标

定义音频转录文本清洗的技术实现：规则清洗、LLM 清洗、时间戳保持、失败降级与测试方案。

---

## 2. 技术栈

- Python 3.11+
- 智谱 GLM-4 / Kimi API
- pydantic 2.x
- 正则表达式 / jieba（中文分词，可选）

---

## 3. 接口契约

文本清洗为内部函数调用，由 ASR Celery 任务在 faster-whisper 完成后调用。

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
text_cleaning:
  enabled: true
  mode: rule          # rule / llm / hybrid
  llm_model: glm-4-flash
  temperature: 0.1
  max_tokens: 2048
  batch_size: 10
  fallback_on_error: true
  filler_words:
    - "嗯"
    - "啊"
    - "哦"
    - "呃"
    - "那个"
    - "就是"
```

---

## 5. 模块设计

### 5.1 RuleCleaner

```python
class RuleCleaner:
    def clean(self, text: str) -> str: ...
```

### 5.2 LlmCleaner

```python
class LlmCleaner:
    def clean_batch(self, segments: list[Segment]) -> list[Segment]: ...
```

### 5.3 TextCleaningService

```python
class TextCleaningService:
    def clean(self, segments: list[Segment]) -> list[Segment]: ...
```

---

## 6. 关键代码实现

### 6.1 规则清洗

```python
import re

FILLER_WORDS = ["嗯", "啊", "哦", "呃", "那个", "就是", "然后", "这个"]
REPEAT_PATTERN = re.compile(r"(\b\w+\b)(\s+\1){2,}")

class RuleCleaner:
    def clean(self, text: str) -> str:
        text = REPEAT_PATTERN.sub(r"\1", text)
        for word in FILLER_WORDS:
            text = text.replace(word, "")
        text = re.sub(r"\s+", " ", text).strip()
        return text
```

### 6.2 LLM 清洗

```python
class LlmCleaner:
    def __init__(self, client, model: str, temperature: float = 0.1):
        self.client = client
        self.model = model
        self.temperature = temperature

    def clean_batch(self, segments: list[dict]) -> list[dict]:
        texts = [s["text"] for s in segments]
        prompt = self._build_prompt(texts)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        cleaned = self._parse_response(response.choices[0].message.content)
        for s, c in zip(segments, cleaned):
            s["text"] = c
        return segments
```

### 6.3 Service 编排

```python
class TextCleaningService:
    def __init__(self, rule_cleaner, llm_cleaner, config):
        self.rule_cleaner = rule_cleaner
        self.llm_cleaner = llm_cleaner
        self.config = config

    def clean(self, segments):
        try:
            for seg in segments:
                seg["text"] = self.rule_cleaner.clean(seg["text"])
            if self.config.mode in ("llm", "hybrid"):
                segments = self.llm_cleaner.clean_batch(segments)
        except Exception:
            if self.config.fallback_on_error:
                return segments  # 原始内容
            raise
        return segments
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| LLM 调用失败 | 500 | LLM_CLEAN_FAILED | 文本清洗失败，已使用原始文本 |
| 清洗后文本为空 | 500 | EMPTY_AFTER_CLEAN | 清洗后文本为空，回退原始 |

---

## 8. Web 端适配要点

- Web 端查看页默认展示清洗后文本
- 提供“查看原文”切换开关
- 清洗失败时自动显示原文并提示

---

## 9. 测试策略

- **单元测试**：规则清洗、LLM 解析、失败 fallback
- **集成测试**：ASR → 清洗 → SRT 重新生成
- **Mock 测试**：模拟 LLM 返回与失败

---

## 10. 检查清单

- [ ] 规则清洗逻辑
- [ ] LLM 清洗调用
- [ ] 失败 fallback
- [ ] SRT 重新生成
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
