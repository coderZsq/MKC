# PRD：[S4-6] 引用跳转：点击跳转到 SRT 时间戳 / PDF 页码

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S4-5_answer_citation_tracing.md](./PRD_S4-5_answer_citation_tracing.md)、[PRD_S2-7_content_view_page.md](./PRD_S2-7_content_view_page.md)、[PRD_S2-2_srt_generation.md](./PRD_S2-2_srt_generation.md)、[PRD_S3-7_flutter_chat_page.md](./PRD_S3-7_flutter_chat_page.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-6 |
| **任务名称** | 引用跳转：点击跳转到 SRT 时间戳 / PDF 页码 |
| **所属史诗** | E6 知识库检索 |
| **故事点** | 3 |
| **优先级** | Should |
| **依赖** | S4-5 答案引用溯源、[PRD_S2-7_content_view_page.md](./PRD_S2-7_content_view_page.md)、[PRD_S2-2_srt_generation.md](./PRD_S2-2_srt_generation.md)、[PRD_S3-7_flutter_chat_page.md](./PRD_S3-7_flutter_chat_page.md) |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为知识库用户，我希望在 AI 回答中点击引用来源卡片时，能够直接跳转到对应资源的确切位置——音频资源跳转到 SRT 时间戳并播放、PDF 资源跳转到指定页码并高亮定位文本——以便快速核对答案与原文出处，无需手动翻找。

---

## 验收标准（AC）

- [ ] **AC-1** 在 S3-7 ChatPage 中点击 `CitationCard`，携带 citation 元数据（resourceId、contentType、page、timestamp、chunkId）触发跳转
- [ ] **AC-2** 音频引用：跳转至内容查看页后，播放器 seek 到 `timestamp` 并自动播放
- [ ] **AC-3** 音频播放过程中，SRT 字幕根据当前播放位置同步高亮当前字幕段
- [ ] **AC-4** PDF 引用：跳转至内容查看页后，自动滚动到 `page` 页并定位/高亮 chunk 文本
- [ ] **AC-5** 路由参数 `t`（秒）/`page`/`chunk` 被正确解析与校验，非法值给出友好提示并降级为默认位置
- [ ] **AC-6** 复用 S2-7 内容查看页与现有搜索/折叠能力，不破坏既有交互
- [ ] **AC-7** 资源不存在或加载失败时显示错误视图与重试按钮
- [ ] **AC-8** Web 端兼容：HTML5 audio seek、PDF 页码跳转与高亮；`flutter test --platform chrome` 通过
- [ ] **AC-9** 单元/Widget 测试覆盖率 80%+

---

## 推荐目录结构

```
client/lib/
├── presentation/
│   ├── pages/
│   │   └── content_view_page.dart          # 复用 S2-7，扩展跳转参数入口
│   ├── widgets/
│   │   ├── audio_player_bar.dart            # 音频播放器与 seek 控制
│   │   ├── srt_sync_highlighter.dart        # 播放位置同步高亮字幕
│   │   ├── pdf_viewer_widget.dart           # PDF 渲染与页码跳转
│   │   ├── citation_card.dart               # S3-7 复用，onTap 传递跳转参数
│   │   └── text_search_bar.dart             # S2-7 复用
│   ├── notifiers/
│   │   ├── content_view_notifier.dart       # S2-7 复用，扩展 jumpToTarget
│   │   └── audio_playback_notifier.dart     # 播放状态与位置流
│   └── providers/
│       ├── content_view_provider.dart       # S2-7 复用
│       └── audio_playback_provider.dart
├── domain/
│   ├── models/
│   │   └── citation_jump_target.dart        # 跳转目标参数模型（不可变值对象）
│   └── services/
│       ├── audio_seek_service.dart          # S2-7 复用，扩展 seekAndPlay
│       └── pdf_jump_service.dart            # PDF 页码跳转与文本定位
└── data/
    └── datasources/
        └── content_remote_datasource.dart   # S2-7 复用
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| flutter_riverpod | 2.5.x | 状态管理 |
| dio | 5.4.x | 资源元数据请求 |
| go_router | 14.1.x | 带参路由与查询参数解析 |
| just_audio | 0.9.x | 音频播放与 seek（Web 端经 just_audio_web 支持） |
| pdfrx | 1.0.x | PDF 渲染、页码跳转与文本定位高亮 |
| intl | 0.19.x | 时间戳格式化 |

---

## 技术要点

### 路由参数

复用 S2-7 的 `/tasks/:id/content` 路由，扩展查询参数：

```
/tasks/{id}/content?type=audio&t=120.5
/tasks/{id}/content?type=pdf&page=3&chunk=chunk_42
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | string | 是 | `audio` / `pdf`，复用 ContentType |
| t | double | 否 | 音频跳转秒数，支持小数（如 120.5） |
| page | int | 否 | PDF 页码，从 1 开始 |
| chunk | string | 否 | 文本块 ID，用于 PDF 文本高亮定位 |

### 跳转流程

1. ChatPage 的 `CitationCard.onTap` 读取 `Citation` 元数据，构造带参 URI
2. `context.push` 至内容查看页，GoRouter 解析查询参数为 `CitationJumpTarget`
3. ContentViewPage 在 `load()` 完成后，根据 `CitationJumpTarget` 执行：
   - 音频：`AudioSeekService.seekAndPlay(timestamp)`，启动 SRT 同步高亮
   - PDF：`PdfJumpService.jumpToPage(page)`，再 `locateChunk(chunkId)` 高亮
4. 跳转参数仅生效一次，后续手动操作不重复触发

### 错误处理

- 路由参数非法（非数字、负数、超出范围）：降级为默认位置并 SnackBar 提示
- 资源不存在（404）：显示错误视图与返回按钮
- 音频/PDF 加载失败：显示重试按钮，保留跳转参数以便重试后继续定位
- Web 端 audio/PDF 不支持：降级为文本视图并提示

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| PDF 文本定位精度不足 | chunk 高亮偏移 | 优先按页码跳转，chunk 文本作为搜索关键词二次定位 |
| just_audio Web seek 精度 | 跳转位置偏差 | 容差 ±0.5s，seek 完成后校正 |
| 大型 PDF 渲染卡顿 | 跳转延迟 | 使用 pdfrx 懒加载页，仅渲染目标页附近 |
| Citation 元数据缺失 page/timestamp | 无法定位 | 缺失时降级到资源首页/起始位置 |

---

## Web 端适配

- 音频播放使用 `just_audio` + `just_audio_web`，HTML5 `<audio>` 支持 seek
- PDF 渲染使用 `pdfrx`（基于 pdf.js），支持 `jumpToPage` 与文本选择
- Web 端引用卡片点击使用 `context.push` 而非新标签页，保持单页体验
- 键盘可访问性：引用卡片可聚焦，回车触发跳转
- 使用 `flutter test --platform chrome` 验证跳转、seek 与高亮

---

## 备注

- 跳转参数模型 `CitationJumpTarget` 为不可变值对象，便于测试与持久化
- SRT 同步高亮复用 S2-7 的 `SrtListView`，新增播放位置监听驱动 `currentSegmentIndex`
- PDF chunk 高亮优先复用 S2-7 的 `TextSearchBar` 搜索匹配机制
- 后续 Sprint 可扩展视频时间戳跳转，预留 `CitationJumpTarget.type` 扩展字段
