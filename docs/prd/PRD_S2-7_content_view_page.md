# PRD：[S2-7] Flutter 内容查看页（SRT/文本）

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 关联文档：[PRD_S2-2_srt_generation.md](./PRD_S2-2_srt_generation.md)、[PRD_S2-6_result_storage.md](./PRD_S2-6_result_storage.md)、[PRD_S1-7_task_progress_push.md](./PRD_S1-7_task_progress_push.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S2-7 |
| **任务名称** | Flutter 内容查看页（SRT/文本） |
| **所属史诗** | E4 音频转录 / E5 PDF 解析 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S2-2 SRT 生成、S2-4 PDF 解析、S2-6 结果存储 |
| **目标 Sprint** | Sprint 2 |

---

## 描述

作为用户，我希望在音频转录或 PDF 解析完成后，能查看生成的 SRT 字幕或解析文本，并支持折叠、搜索与时间戳/页码跳转。本任务在 Flutter 端实现内容查看页，复用 S1-7 的任务状态通道。

---

## 验收标准（AC）

- [ ] **AC-1** 任务中心点击“查看内容”进入 ContentViewPage
- [ ] **AC-2** 音频任务展示 SRT 字幕列表，点击时间戳跳转到音频播放器对应位置
- [ ] **AC-3** PDF 任务展示结构化文本，按页折叠，点击页码跳转
- [ ] **AC-4** 支持文本搜索与高亮
- [ ] **AC-5** 支持“查看原文”与“清洗后文本”切换（音频）
- [ ] **AC-6** 加载失败时显示重试按钮
- [ ] **AC-7** 单元/Widget 测试覆盖率 80%+

---

## 推荐目录结构

```
client/
├── lib/
│   ├── presentation/
│   │   ├── pages/
│   │   │   └── content_view_page.dart
│   │   ├── widgets/
│   │   │   ├── srt_list_view.dart
│   │   │   ├── pdf_text_view.dart
│   │   │   └── text_search_bar.dart
│   │   └── notifiers/
│   │       └── content_view_notifier.dart
│   ├── domain/
│   │   ├── models/
│   │   │   ├── subtitle_segment.dart
│   │   │   └── parsed_page.dart
│   │   └── repositories/
│   │       └── content_repository.dart
│   └── data/
│       └── datasources/
│           └── content_remote_datasource.dart
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| flutter_riverpod | 2.5.x | 状态管理 |
| dio | 5.4.x | 文件下载 |
| flutter_markdown | 0.7.x | Markdown 文本渲染（可选） |
| just_audio | 0.9.x | 音频播放器（时间戳跳转） |

---

## 技术要点

### SRT 解析

```dart
class SubtitleSegment {
  final int index;
  final Duration start;
  final Duration end;
  final String text;
}
```

### 文本折叠策略

- PDF 按页折叠，默认展示当前页
- 音频文本按 30 秒段落折叠

### 搜索高亮

- 用户输入关键词后，在当前内容中高亮匹配
- 支持上一个/下一个跳转

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 大文件解析文本长 | 页面卡顿 | 使用 ListView.builder + 分页加载 |
| 音频播放器时间戳跳转精度 | 体验差 | 使用 just_audio seek 精确跳转 |
| 搜索结果定位困难 | 可用性差 | 提供导航按钮与结果计数 |

---

## Web 端适配

Web 端 Flutter 内容查看页需处理：
- 音频播放使用 `just_audio` Web 支持，时间戳跳转需测试
- 大文本列表使用 `ListView.builder`
- 搜索使用 `TextField` + 浏览器输入键盘兼容
- 使用 `flutter test --platform chrome` 验证 Widget 渲染

---

## 备注

- 内容查看页初始版本以只读为主，编辑功能后续扩展
- 支持分享功能（后续 Sprint）
- 需要缓存已下载内容，避免重复请求
