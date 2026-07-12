# 技术文档：[S4-6] 引用跳转：点击跳转到 SRT 时间戳 / PDF 页码

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 级别：前端/移动端工程师
> 关联 PRD：[../prd/PRD_S4-6_citation_jump_navigation.md](../prd/PRD_S4-6_citation_jump_navigation.md)

---

## 1. 文档目标

定义引用跳转功能的技术实现：带参路由解析、CitationCard 跳转触发、音频 seekTo 与 SRT 同步高亮、PDF 页码跳转与 chunk 高亮、错误处理与 Web 端适配。

---

## 2. 技术栈

- Flutter 3.22+ / Dart 3.4+
- flutter_riverpod 2.5.x（状态管理）
- dio 5.4.x（资源元数据请求）
- go_router 14.1.x（带参路由）
- just_audio 0.9.x（音频播放）
  - 选型理由：统一移动端与 Web 端 API（just_audio_web 提供 HTML5 audio 后端），seek 精度高，社区活跃，且与 S2-7 已规划依赖保持一致
- pdfrx 1.0.x（PDF 渲染）
  - 选型理由：MIT 许可、无商业注册、原生支持 `jumpToPage` 与文本提取（用于 chunk 高亮定位），Web 端基于 pdf.js 兼容良好；相比 syncfusion_flutter_pdfviewer 避免社区版授权限制与体积
- intl 0.19.x（时间格式化）

---

## 3. 接口契约

### 3.1 资源内容接口（复用 S2-7）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api/v1/tasks/{id}/content?type=audio` | Bearer JWT | 获取 SRT 字幕与音频地址 |
| GET | `/api/v1/tasks/{id}/content?type=pdf` | Bearer JWT | 获取 PDF 页面文本与文件地址 |

### 3.2 路由参数契约

```
GET /tasks/{id}/content?type=audio&t=120.5
GET /tasks/{id}/content?type=pdf&page=3&chunk=chunk_42
```

| 参数 | 类型 | 必填 | 校验规则 | 示例 |
|---|---|---|---|---|
| type | string | 是 | 枚举 `audio`/`pdf` | `audio` |
| t | double | 否 | >= 0，精度 0.1s | `120.5` |
| page | int | 否 | >= 1 | `3` |
| chunk | string | 否 | 非空字符串 | `chunk_42` |

### 3.3 错误码

| HTTP | code | 说明 | 客户端处理 |
|---|---|---|---|
| 401 | unauthorized | JWT 失效 | 跳转登录页 |
| 404 | task_not_found | 资源不存在 | 错误视图 + 返回 |
| 409 | task_not_completed | 任务未完成 | 刷新按钮 |
| 422 | invalid_param | 跳转参数非法 | 降级默认位置 + SnackBar |

---

## 4. 配置

在 `lib/config/constants.dart` 新增跳转参数相关常量：

```dart
class CitationJumpConfig {
  /// seek 容差（秒）
  static const double seekToleranceSeconds = 0.5;
  /// SRT 同步高亮节流（毫秒）
  static const int srtSyncThrottleMs = 100;
  /// PDF 跳转预渲染页数（前后）
  static const int pdfPreloadRange = 1;
}
```

无新增环境变量；音频/PDF 地址复用 S2-7 内容接口返回字段。

---

## 5. 模块设计

### 5.1 CitationJumpTarget（值对象）

```dart
class CitationJumpTarget {
  const CitationJumpTarget({
    required this.contentType,
    this.timestampSeconds,
    this.page,
    this.chunkId,
  });

  final ContentType contentType;
  final double? timestampSeconds;
  final int? page;
  final String? chunkId;

  bool get hasAudioTarget => timestampSeconds != null;
  bool get hasPdfTarget => page != null;

  factory CitationJumpTarget.fromQuery(Map<String, String> params) {
    // 解析并校验 t/page/chunk，非法值返回对应字段为 null
  }

  CitationJumpTarget copyWith({
    ContentType? contentType,
    double? timestampSeconds,
    int? page,
    String? chunkId,
  }) {
    return CitationJumpTarget(
      contentType: contentType ?? this.contentType,
      timestampSeconds: timestampSeconds ?? this.timestampSeconds,
      page: page ?? this.page,
      chunkId: chunkId ?? this.chunkId,
    );
  }
}
```

### 5.2 CitationCard（扩展 onTap）

```dart
class CitationCard extends StatelessWidget {
  const CitationCard({super.key, required this.citation});
  final Citation citation;

  void _onTap(BuildContext context) {
    if (!isValidResourceId(citation.resourceId)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invalid citation resource ID')),
      );
      return;
    }
    final uri = Uri(
      path: '/tasks/${citation.resourceId}/content',
      queryParameters: _buildQuery(citation),
    );
    context.push(uri.toString());
  }

  Map<String, String> _buildQuery(Citation c) => {
        'type': c.contentType.paramValue,
        if (c.timestamp != null)
          't': (c.timestamp!.inMilliseconds / 1000).toStringAsFixed(1),
        if (c.page != null && c.page!.isNotEmpty) 'page': c.page!,
        // chunkId 来自 S4-5 citation metadata 扩展字段
      };
}
```

### 5.3 ContentViewPage（扩展跳转入口）

```dart
class ContentViewPage extends ConsumerStatefulWidget {
  const ContentViewPage({
    required this.taskId,
    required this.contentType,
    this.jumpTarget,
    super.key,
  });

  final String taskId;
  final ContentType contentType;
  final CitationJumpTarget? jumpTarget;
}
```

GoRouter builder 解析查询参数并注入 `jumpTarget`，加载完成后在 `_applyJump` 中执行定位。

### 5.4 AudioPlaybackNotifier

```dart
class AudioPlaybackNotifier extends StateNotifier<AudioPlaybackState> {
  AudioPlaybackNotifier(this._player) : super(AudioPlaybackState.initial());
  final AudioPlayer _player;

  Future<void> seekAndPlay(Duration position) async {
    await _player.seek(position);
    await _player.play();
  }

  Stream<Duration> get positionStream => _player.positionStream;
}
```

### 5.5 PdfJumpService

```dart
class PdfJumpService {
  Future<void> jumpToPage(PdfViewerController controller, int page) async {
    if (page < 1) return;
    await controller.jumpToPage(page);
  }

  Future<void> locateChunk(String chunkId, String chunkText) async {
    // 将 chunkText 作为关键词复用搜索机制高亮
  }
}
```

### 5.6 SrtSyncHighlighter

监听播放位置流，节流更新当前字幕索引，驱动 `SrtListView` 高亮当前段。

---

## 6. 关键代码实现

### 6.1 路由参数解析

```dart
GoRoute(
  path: contentViewRoute,
  builder: (_, state) {
    final taskId = state.pathParameters['id']!;
    final contentType = ContentType.fromParam(
      state.uri.queryParameters['type'],
    );
    final jumpTarget = CitationJumpTarget.fromQuery(
      state.uri.queryParameters,
    );
    return ContentViewPage(
      taskId: taskId,
      contentType: contentType,
      jumpTarget: jumpTarget.contentType == contentType ? jumpTarget : null,
    );
  },
),
```

### 6.2 音频 seekTo 并播放

```dart
Future<void> _applyAudioJump(CitationJumpTarget target) async {
  final seconds = target.timestampSeconds;
  if (seconds == null) return;
  final clamped = seconds.clamp(0.0, double.infinity);
  await ref.read(audioPlaybackProvider.notifier).seekAndPlay(
        Duration(milliseconds: (clamped * 1000).round()),
      );
}
```

### 6.3 SRT 同步高亮

```dart
ref.listen<Duration>(currentPositionProvider, (previous, position) {
  final segments = state.content is AudioContent
      ? (state.content as AudioContent).segments
      : const <SubtitleSegment>[];
  final index = _findCurrentSegment(segments, position);
  if (index != state.currentSegmentIndex) {
    ref.read(_provider.notifier).setCurrentSegmentIndex(index);
  }
});

int _findCurrentSegment(List<SubtitleSegment> segments, Duration pos) {
  for (var i = 0; i < segments.length; i++) {
    if (pos >= segments[i].start && pos < segments[i].end) return i;
  }
  return -1;
}
```

### 6.4 PDF 页码跳转与高亮

```dart
Future<void> _applyPdfJump(CitationJumpTarget target) async {
  final page = target.page;
  if (page == null || page < 1) return;
  await ref.read(pdfJumpServiceProvider).jumpToPage(_pdfController, page);
  if (target.chunkId != null) {
    final chunkText = _resolveChunkText(target.chunkId!);
    if (chunkText != null) {
      ref.read(_provider.notifier).onSearchChanged(chunkText);
    }
  }
}
```

---

## 7. 错误映射

| 场景 | 处理方式 |
|---|---|
| 路由参数 t 非数字/负数 | 降级到 0 秒，SnackBar 提示「时间戳无效」 |
| 路由参数 page 超出范围 | 降级到第 1 页，SnackBar 提示「页码无效」 |
| chunk 文本未匹配 | 仅跳转页码，不高亮 |
| 音频加载失败 | 显示重试按钮，保留 jumpTarget |
| PDF 加载失败 | 显示重试按钮，保留 jumpTarget |
| 资源 404 | 错误视图 + 返回按钮 |
| JWT 失效 | GoRouter redirect 跳转登录 |

---

## 8. Web 端适配要点

- 音频：`just_audio_web` 后端基于 HTML5 `<audio>`，seek 通过 `audio.currentTime` 实现
- PDF：`pdfrx` Web 端基于 pdf.js，`jumpToPage` 调用 pdf.js 的 `pageNumber` 跳转
- 引用卡片点击使用 `context.push` 保持单页导航，避免新标签页丢失会话状态
- SRT 同步高亮在 Web 端使用 `positionStream` 节流（100ms），避免高频 setState
- 使用 `flutter test --platform chrome` 验证 seek、页码跳转与高亮渲染

---

## 9. 测试策略

- **单元测试**：`CitationJumpTarget.fromQuery` 参数解析与校验、`_findCurrentSegment` 索引计算、`PdfJumpService` 页码边界
- **Widget 测试**：`CitationCard` 构造 URI、`ContentViewPage` 接收 jumpTarget 后触发 seek/jump、SRT 高亮随位置变化
- **集成测试**：ChatPage 点击引用 -> ContentViewPage 定位 -> 验证播放器位置/页码
- **Web 测试**：`flutter test --platform chrome` 覆盖跳转与渲染
- 覆盖率目标 80%+，重点覆盖参数解析与跳转编排逻辑

---

## 10. 检查清单

- [ ] `CitationJumpTarget` 值对象与参数解析
- [ ] `CitationCard` onTap 构造带参 URI
- [ ] GoRouter 解析查询参数注入 jumpTarget
- [ ] `AudioPlaybackNotifier` seekAndPlay
- [ ] SRT 同步高亮（位置流 -> 当前段索引）
- [ ] `PdfJumpService` jumpToPage 与 chunk 高亮
- [ ] 错误处理与降级策略
- [ ] Web 端兼容性验证
- [ ] Widget 测试覆盖率 80%+
- [ ] flutter analyze 通过，无硬编码密钥
