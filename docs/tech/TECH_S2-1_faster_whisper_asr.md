# 技术文档：[S2-1] 集成 faster-whisper 实现 ASR

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S2-1_faster_whisper_asr.md](../prd/PRD_S2-1_faster_whisper_asr.md)

---

## 1. 文档目标

定义 AI Service 中 faster-whisper ASR 转录模块的技术实现：接口契约、模型加载、音频预处理、分片转录、进度上报、错误处理与测试策略。

---

## 2. 技术栈

- Python 3.11+
- Flask 2.3+ / FastAPI 0.110+
- faster-whisper 1.0+
- ffmpeg + ffmpeg-python
- librosa / soundfile
- Celery 5.4+ + Redis Broker
- MinIO Python SDK
- pydantic 2.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/ai/v1/asr` | Internal API Key | 提交 ASR 异步任务 |
| GET | `/ai/v1/tasks/{task_id}` | Internal API Key | 查询任务状态（复用通用） |

### 请求示例

```json
POST /ai/v1/asr
Headers: X-Internal-Key: <key>
{
  "task_id": "01922b9c-...",
  "resource_id": "01922b9c-...",
  "audio_url": "minio://resources/.../audio.mp3",
  "language": "zh",
  "model": "small"
}
```

### 响应示例

```json
{
  "task_id": "01922b9c-...",
  "status": "pending",
  "message": "ASR task queued"
}
```

### 错误码映射

| HTTP | Error Code | 说明 |
|---|---|---|
| 400 | INVALID_AUDIO | 音频格式不支持或损坏 |
| 404 | MODEL_NOT_FOUND | 模型路径不存在 |
| 503 | ASR_UNAVAILABLE | 模型加载失败 |
| 500 | ASR_INTERNAL_ERROR | 转录内部错误 |

---

## 4. 配置

新增 `config/ai.yaml`：

```yaml
asr:
  model_dir: /models/whisper
  default_model: small
  fallback_model: tiny
  device: auto
  compute_type: int8
  beam_size: 5
  vad_filter: true
  chunk_length: 30
  language: zh
  sample_rate: 16000
  progress_interval: 5.0  # 秒
```

环境变量：

- `WHISPER_MODEL_DIR`：模型目录
- `ASR_DEVICE`：cpu/cuda
- `ASR_COMPUTE_TYPE`：int8/fp16/fp32

---

## 5. 模块设计

### 5.1 WhisperEngine

```python
class WhisperEngine:
    def __init__(self, model_name: str, config: AsrConfig): ...
    def load(self) -> None: ...
    def transcribe(self, audio_path: Path) -> Iterator[Segment]: ...
```

### 5.2 AudioProcessor

```python
class AudioProcessor:
    def convert_to_wav(self, source: Path, target: Path) -> Path: ...
    def chunk_audio(self, wav_path: Path, chunk_length: int, overlap: int = 1) -> Iterator[AudioChunk]: ...
    def vad_split(self, wav_path: Path) -> Iterator[AudioChunk]: ...
```

### 5.3 AsrService

```python
class AsrService:
    def __init__(self, engine: WhisperEngine, processor: AudioProcessor, repo: TaskRepository): ...
    async def process(self, task: AsrTask) -> AsrResult: ...
```

### 5.4 AsrCeleryTask

```python
@app.task(bind=True, max_retries=3)
def run_asr(self, task_id: str, payload: dict):
    ...
```

---

## 6. 关键代码实现

### 6.1 WhisperEngine 转录

```python
from faster_whisper import WhisperModel
from pathlib import Path

class WhisperEngine:
    def __init__(self, model_name: str, device: str = "auto", compute_type: str = "int8"):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

    def load(self) -> None:
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
            download_root=os.getenv("WHISPER_MODEL_DIR", "/models/whisper"),
        )

    def transcribe(self, audio_path: Path, language: str | None = None):
        if not self._model:
            self.load()
        segments, info = self._model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        for segment in segments:
            yield {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob,
            }
```

### 6.2 音频转码

```python
import ffmpeg

def convert_to_wav(input_path: Path, output_path: Path, sample_rate: int = 16000):
    try:
        ffmpeg.input(str(input_path)).output(
            str(output_path),
            ar=sample_rate,
            ac=1,
            acodec="pcm_s16le",
        ).run(overwrite_output=True, quiet=True)
    except ffmpeg.Error as e:
        raise AudioProcessingError(f"ffmpeg convert failed: {e.stderr}")
```

### 6.3 进度上报

```python
def report_progress(task_id: str, progress: int, status: str):
    requests.patch(
        f"{GATEWAY_URL}/api/v1/internal/tasks/{task_id}/progress",
        json={"progress": progress, "status": status},
        headers={"X-Internal-Key": INTERNAL_KEY},
        timeout=5,
    )
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 音频格式不支持 | 400 | INVALID_AUDIO | 无法解析音频文件 |
| 模型加载失败 | 503 | MODEL_LOAD_ERROR | ASR 模型不可用 |
| 转录异常 | 500 | ASR_FAILED | 转录失败，请重试 |
| 任务不存在 | 404 | TASK_NOT_FOUND | 任务不存在 |

---

## 8. Web 端适配要点

ASR 接口为 AI Service 内部任务接口，Web 端不直接调用。进度与结果通过 Gateway SSE 与任务详情 API 暴露。

---

## 9. 测试策略

- **单元测试**：`WhisperEngine` 加载、`AudioProcessor` 转码、分片逻辑
- **集成测试**：提交 ASR 任务 → 模拟 faster-whisper 返回 → 验证进度上报
- **E2E 测试**：上传 MP3 → 等待任务完成 → 检查转录结果非空
- **Mock 策略**：使用 tiny 模型或预录 segment 结果，避免 CI 下载大模型

---

## 10. 检查清单

- [ ] WhisperEngine 加载与转录
- [ ] AudioProcessor 转码与分片
- [ ] ASR Celery 任务编排
- [ ] 进度上报 Gateway
- [ ] 错误 fallback 与模型切换
- [ ] 测试覆盖率 80%+
- [ ] OpenAPI/文档同步更新
