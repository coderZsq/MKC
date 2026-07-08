# PRD：[S2-2] 生成 SRT 字幕文件

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[PRD_S2-1_faster_whisper_asr.md](./PRD_S2-1_faster_whisper_asr.md)、[TECH_S2-1_faster_whisper_asr.md](../tech/TECH_S2-1_faster_whisper_asr.md)、[TECH_S2-6_result_storage.md](../tech/TECH_S2-6_result_storage.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-2 |
| **任务名称** | 生成 SRT 字幕文件 |
| **所属史诗** | E4 音频转录 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S2-1 faster-whisper ASR |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望在 MP3 转录完成后获得标准的 SRT 字幕文件，以便在内容查看页中高亮浏览与跳转。本任务将 faster-whisper 输出的 segments 转换为符合 SRT 规范的字幕文件，并合并过短片段。

---

## 验收标准（AC）

- [ ] **AC-1** 从 ASR segments 生成标准 SRT 格式（序号、时间码、文本）
- [ ] **AC-2** 时间码格式 `HH:MM:SS,mmm --> HH:MM:SS,mmm`
- [ ] **AC-3** 相邻短句按最小时长（如 1s）与最大字符数（如 80 字）合并
- [ ] **AC-4** 生成的 SRT 文件写入 MinIO，URL 保存到 task.result
- [ ] **AC-5** 支持 WebVTT 导出（可选）
- [ ] **AC-6** 生成失败时返回 500 并记录日志
- [ ] **AC-7** 单元测试覆盖率 80%+

---

## 推荐目录结构

```
ai-service/
├── app/
│   ├── services/
│   │   ├── srt_generator.py      # SRT 生成器
│   │   └── segment_merger.py     # 片段合并
│   └── utils/
│       └── timecode.py           # 时间码格式化
└── tests/
    └── unit/test_srt_generator.py
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python 标准库 | - | 文件与时间格式化 |
| pydantic | 2.x | Segment 数据校验 |

---

## 技术要点

### SRT 格式示例

```
1
00:00:05,000 --> 00:00:08,200
大家好，欢迎参加本次分享。

2
00:00:08,200 --> 00:00:12,500
今天我们讨论多媒体知识库。
```

### 合并策略

- 最小显示时长：1.0s
- 最大显示时长：6.0s
- 最大字符数：80
- 置信度阈值低于 -0.5 的片段标记颜色（后续消费）

### 输入数据结构

```json
[
  {"start": 5.0, "end": 8.2, "text": "大家好", "confidence": -0.1}
]
```

### 输出流程

1. 读取 ASR 结果
2. 合并与排序 segments
3. 生成 SRT 字符串
4. 上传至 MinIO `results/{task_id}/subtitle.srt`
5. 更新 task.result.subtitle_url

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| ASR 输出时间戳跳变 | SRT 时间码不连续 | 归并排序并修复负持续片段 |
| 单句过长 | 字幕超屏 | 按字符/时长拆分 |

---

## Web 端适配

Web 端内容查看页加载 SRT 并解析为字幕列表，点击时间戳可跳转到音频对应位置。字幕加载失败时显示错误提示与重试按钮。

---

## 备注

- SRT 为默认输出，WebVTT 可在后续 Sprint 扩展
- 原始 segments 也保留，供 S2-3 文本清洗使用
- 同一任务支持重新生成（调用 S2-1 + S2-2 流程）
