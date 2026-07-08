# 技术文档：[S2-2] 生成 SRT 字幕文件

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S2-2_srt_generation.md](../prd/PRD_S2-2_srt_generation.md)

---

## 1. 文档目标

定义将 ASR segments 转换为 SRT 字幕文件的实现方案，包括合并策略、时间码格式化、MinIO 存储与错误处理。

---

## 2. 技术栈

- Python 3.11+
- pydantic 2.x
- MinIO Python SDK
- 标准库 io / datetime

---

## 3. 接口契约

SRT 生成为内部服务函数，不直接暴露 HTTP 接口。由 AsrCeleryTask 在完成 faster-whisper 转录后调用。

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
srt:
  min_duration: 1.0
  max_duration: 6.0
  max_chars: 80
  output_format: srt  # srt / vtt
```

---

## 5. 模块设计

### 5.1 SegmentMerger

```python
class SegmentMerger:
    def merge(self, segments: list[Segment]) -> list[Segment]: ...
```

### 5.2 SrtGenerator

```python
class SrtGenerator:
    def generate(self, segments: list[Segment]) -> str: ...
    def save_to_minio(self, content: str, key: str) -> str: ...
```

### 5.3 TimecodeUtil

```python
def format_timecode(seconds: float) -> str: ...
```

---

## 6. 关键代码实现

### 6.1 时间码格式化

```python
def format_timecode(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, millis = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
```

### 6.2 Segment 合并

```python
def merge_segments(segments, min_duration=1.0, max_duration=6.0, max_chars=80):
    merged = []
    current = None
    for seg in segments:
        if current is None:
            current = seg.copy()
            continue
        duration = seg["end"] - current["start"]
        chars = len(current["text"] + seg["text"])
        if duration < min_duration or (duration < max_duration and chars < max_chars):
            current["end"] = seg["end"]
            current["text"] += " " + seg["text"]
        else:
            merged.append(current)
            current = seg.copy()
    if current:
        merged.append(current)
    return merged
```

### 6.3 SRT 生成

```python
def generate_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = format_timecode(seg["start"])
        end = format_timecode(seg["end"])
        lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
    return "\n".join(lines)
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| segments 为空 | 500 | EMPTY_SEGMENTS | 无可用转录结果 |
| MinIO 上传失败 | 500 | STORAGE_ERROR | 字幕存储失败 |
| 时间戳非法 | 500 | INVALID_TIMESTAMP | 时间码格式错误 |

---

## 8. Web 端适配要点

- SRT 文件通过 Gateway 静态资源或签名 URL 下发
- Web 端使用字幕解析器拆分为列表，支持点击时间戳跳转
- Web 端使用 AudioPlayer 按字幕时间戳定位

---

## 9. 测试策略

- **单元测试**：合并算法、时间码格式化、SRT 字符串输出
- **集成测试**：从 ASR 结果 → SRT → MinIO 全链路
- **Mock 测试**：模拟 MinIO 上传失败

---

## 10. 检查清单

- [ ] Segment 合并逻辑
- [ ] SRT 格式化输出
- [ ] MinIO 上传
- [ ] 错误处理
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
