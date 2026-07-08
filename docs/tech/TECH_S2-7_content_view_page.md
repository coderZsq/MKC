# 技术文档：[S2-7] Flutter 内容查看页（SRT/文本）

> 版本：v1.0
> 日期：2026-07-08
> 作者：朱双泉
> 级别：前端/移动端/Web 端工程师
> 关联 PRD：[../prd/PRD_S2-7_content_view_page.md](../prd/PRD_S2-7_content_view_page.md)

---

## 1. 文档目标

定义 Flutter 内容查看页的技术实现：数据模型、状态管理、UI 组件、搜索高亮、时间戳/页码跳转与测试策略。

---

## 2. 技术栈

- Flutter 3.22+
- Dart 3.4+
- flutter_riverpod 2.5+
- dio 5.4+
- just_audio 0.9+

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api/v1/tasks/{task_id}/result` | Bearer JWT | 获取结果文件 URL（复用 S2-6） |
| GET | 签名 URL | - | 下载 SRT/JSON 文件 |

---

## 4. 配置

新增 `lib/core/config.dart`：

```dart
class ContentConfig {
  static const segmentFoldDuration = Duration(seconds: 30);
  static const searchDebounceMs = 300;
  static const maxHighlightMatches = 100;
}
```

---

## 5. 模块设计

### 5.1 Data Layer

- `ContentRemoteDataSource`: 下载结果文件
- `ContentRepository`: 解析 SRT/JSON 并返回模型

### 5.2 Domain Layer

- `SubtitleSegment`: 字幕段模型
- `ParsedPage`: PDF 页模型
- `ContentType`: `audio` / `pdf`

### 5.3 Presentation Layer

- `ContentViewPage`: 页面入口
- `SrtListView`: SRT 字幕列表
- `PdfTextView`: PDF 文本视图
- `ContentViewNotifier`: 状态管理

---

## 6. 关键代码实现

### 6.1 SRT 解析

```dart
List<SubtitleSegment> parseSrt(String srt) {
  final segments = <SubtitleSegment>[];
  final blocks = srt.split('\n\n');
  for (final block in blocks) {
    final lines = block.trim().split('\n');
    if (lines.length < 3) continue;
    final times = lines[1].split(' --> ');
    segments.add(SubtitleSegment(
      index: int.parse(lines[0]),
      start: _parseTimecode(times[0]),
      end: _parseTimecode(times[1]),
      text: lines.skip(2).join('\n'),
    ));
  }
  return segments;
}
```

### 6.2 状态管理

```dart
class ContentViewNotifier extends StateNotifier<ContentViewState> {
  ContentViewNotifier(this._repository) : super(ContentViewState.initial());

  final ContentRepository _repository;

  Future<void> load(String taskId) async { ... }
  void search(String keyword) { ... }
  void jumpToMatch(int index) { ... }
}
```

### 6.3 时间戳跳转

```dart
void seekToSegment(SubtitleSegment segment) {
  _audioPlayer.seek(segment.start);
}
```

---

## 7. 错误映射

| 场景 | 处理方式 |
|---|---|
| 下载失败 | 显示重试按钮 |
| 解析失败 | 显示“内容格式错误” |
| 任务未完成 | 显示“处理中，请稍后” |

---

## 8. Web 端适配要点

- Web 端音频播放使用 `just_audio` Web 实现，seek 需兼容
- 大文本使用 `ListView.builder` 避免一次性构建
- 使用 `flutter test --platform chrome` 验证

---

## 9. 测试策略

- **单元测试**：SRT 解析、JSON 解析、搜索高亮
- **Widget 测试**：列表渲染、搜索、跳转、错误重试
- **集成测试**：真实任务 → 下载结果 → 展示内容
- **E2E 测试**：上传 MP3 → 查看 SRT → 点击时间戳跳转

---

## 10. 检查清单

- [ ] SRT 解析器
- [ ] PDF 文本视图
- [ ] 搜索高亮
- [ ] 时间戳/页码跳转
- [ ] 错误重试
- [ ] 测试覆盖率 80%+
- [ ] Web 端验证
- [ ] OpenAPI/文档同步更新
