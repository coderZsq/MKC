# PRD：[S2-1] 集成 faster-whisper 实现 ASR

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[TECH_S0-8_python_ai_service_skeleton.md](../tech/TECH_S0-8_python_ai_service_skeleton.md)、[TECH_S2-2_srt_generation.md](../tech/TECH_S2-2_srt_generation.md)、[TECH_S2-8_async_task_retry.md](../tech/TECH_S2-8_async_task_retry.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-1 |
| **任务名称** | 集成 faster-whisper 实现 ASR |
| **所属史诗** | E4 音频转录 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S0-8 Python AI Service 骨架、S1-5 任务状态 API |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望上传的 MP3 文件被自动转录成文本，以便后续检索和阅读。本任务在 AI Service 中集成 faster-whisper，支持音频预处理、分片转录与结果返回，并对外提供异步转录任务入口。

---

## 验收标准（AC）

- [ ] **AC-1** AI Service 提供 `POST /ai/v1/asr` 异步任务接口，接收 resource_id 与音频 URL
- [ ] **AC-2** faster-whisper 支持 `tiny` / `small` / `base` / `large-v3` 模型切换（配置化）
- [ ] **AC-3** 支持 MP3/WAV/M4A 输入，自动转码为 16kHz 单声道 PCM
- [ ] **AC-4** 长音频按 30s 滑动窗口分片，VAD 过滤静音段，避免显存溢出
- [ ] **AC-5** 输出包含逐段文本、开始时间、结束时间、置信度分数
- [ ] **AC-6** 转录过程中定期上报 `progress` 到 Gateway 任务状态接口
- [ ] **AC-7** 转录失败时返回明确错误码，并触发任务失败状态
- [ ] **AC-8** 单元/集成测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── api/
│   │   └── asr.py              # ASR 任务 API
│   ├── services/
│   │   ├── asr_service.py      # 转录 orchestration
│   │   ├── audio_processor.py  # 音频预处理
│   │   └── whisper_engine.py   # faster-whisper 封装
│   └── tasks/
│       └── asr_task.py         # Celery 异步任务
├── config/
│   └── ai.yaml                 # 模型配置
└── tests/
    ├── unit/test_whisper_engine.py
    └── integration/test_asr_api.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| faster-whisper | 1.0.x | 本地 ASR 推理 |
| ffmpeg-python | 0.2.x | 音频转码与格式转换 |
| librosa | 0.10.x | 音频加载与重采样 |
| soundfile | 0.12.x | PCM 读写 |
| numpy | 1.26.x | 音频数组处理 |
| Celery | 5.4.x | 异步任务队列 |
| pydub | 0.25.x | 音频分片（备选） |

---

## 技术要点

### 模型配置

```yaml
asr:
  model: small          # tiny/base/small/large-v3
  device: auto          # cpu/cuda/auto
  compute_type: int8    # int8/fp16/fp32
  beam_size: 5
  best_of: 5
  vad_filter: true
  vad_parameters:
    min_silence_duration_ms: 500
    threshold: 0.5
  chunk_length: 30      # 秒
  language: zh
```

### 音频预处理流程

1. 使用 ffmpeg 将输入转换为 WAV 16kHz 单声道
2. 计算音频时长与总帧数
3. 按 `chunk_length` 分片，重叠 1s 避免截断单词
4. VAD 过滤静音段，提升速度

### 接口/事件格式

**请求**

```json
{
  "resource_id": "01922b9c-...",
  "audio_url": "minio://resources/.../audio.mp3",
  "language": "zh",
  "model": "small"
}
```

**Worker 进度上报**

```json
{
  "task_id": "...",
  "progress": 35,
  "status": "running"
}
```

### 错误处理与降级策略

- 模型文件缺失：启动时预下载，失败时返回 503 并提示检查模型路径
- 显存不足：自动切换更小的模型或 CPU 回退（配置 `fallback_model: tiny`）
- 音频格式不支持：ffmpeg 转换失败返回 400
- 转录质量低：返回低置信度提示，由下游 S2-3 文本清洗补充

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| faster-whisper 首次下载模型慢 | 环境搭建阻塞 | 使用 .cache/whisper 本地缓存，CI 中预下载 |
| 长音频显存不足 | 转录失败 | 分片推理 + CPU fallback |
| 中文标点与数字识别差 | 输出质量差 | 后续 S2-3 LLM 后处理修正 |
| ffmpeg 未安装 | 预处理失败 | Docker 镜像内置 ffmpeg |

---

## Web 端适配

本任务主要为后端 AI Service 能力，Web 端不直接调用 ASR 接口。Web 端 Flutter 通过任务状态 SSE 查看转录进度，详细内容展示在 S2-7 内容查看页。

---

## 备注

- 模型大小建议本地开发使用 `small` 或 `base`，生产环境可切换 `large-v3`
- 转录结果原始格式在内存中保留，由 S2-2 生成 SRT，S2-6 写入 MinIO
- 同一资源支持重新发起 ASR 任务（复用 S1-5 任务创建能力）
