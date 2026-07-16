# 技术文档：[S5-10] Flutter 多端适配检查

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：前端工程师
> 关联 PRD：[../prd/PRD_S5-10_flutter_multiplatform_compatibility.md](../prd/PRD_S5-10_flutter_multiplatform_compatibility.md)

---

## 1. 文档目标

定义 Flutter iOS、Android、Web 多端兼容检查范围、平台能力封装、响应式布局、文件上传、SSE 降级和测试策略。

---

## 2. 技术栈

- Flutter 3.22+
- Dart 3.x
- Riverpod 2.x
- Dio 5.x
- file_picker
- flutter_test / integration_test

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/files` | Bearer JWT | 多端上传 |
| GET | `/api/v1/tasks/:id` | Bearer JWT | 任务状态 |
| GET | `/api/v1/chat/stream` | Bearer JWT | SSE 问答 |

平台能力：

```dart
class PlatformCapabilities {
  final bool supportsFilePicker;
  final bool supportsSse;
  final bool isWeb;
}
```

---

## 4. 配置

```dart
const breakpoints = AppBreakpoints(
  compact: 600,
  medium: 1024,
  expanded: 1440,
);
```

Web 构建：

```bash
flutter build web --dart-define=API_BASE_URL=https://mkc.example.com
```

---

## 5. 模块设计

- `PlatformCapabilities`：集中判断 Web、移动端和能力差异。
- `ResponsiveScaffold`：统一断点布局。
- `UploadAdapter`：封装移动端和 Web 文件选择差异。
- `StreamAnswerClient`：SSE 断线重试和非流式降级。
- `CompatibilityChecklist`：发布前检查文档。

---

## 6. 关键代码实现

```dart
Widget build(BuildContext context) {
  final width = MediaQuery.sizeOf(context).width;
  if (width < AppBreakpoints.compact) {
    return const ChatCompactLayout();
  }
  return const ChatWideLayout();
}
```

```dart
Future<PickedFile?> pickUploadFile(PlatformCapabilities caps) async {
  if (!caps.supportsFilePicker) {
    throw const AppError(code: 'FILE_PICKER_UNSUPPORTED');
  }
  return _filePicker.pick();
}
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| Web 文件选择失败 | N/A | FILE_PICKER_FAILED | 文件选择失败 |
| 平台不支持能力 | N/A | PLATFORM_UNSUPPORTED | 当前平台暂不支持该能力 |
| SSE 断流 | N/A | STREAM_DISCONNECTED | 回答连接已断开 |
| 布局约束异常 | N/A | LAYOUT_OVERFLOW | 页面布局溢出 |

---

## 8. Web 端适配要点

重点覆盖 Flutter Web：CORS、SSE、上传大小、浏览器兼容、路由 base href、静态资源缓存和窄屏浏览器布局。

---

## 9. 测试策略

- Widget 测试：断点布局、错误提示、引用面板。
- 集成测试：登录、上传、任务状态、问答。
- 静态检查：`flutter analyze`、`flutter test`、`flutter build web`。
- 手工检查：iOS/Android/Web 三端主流程。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] Widget/集成测试通过
- [ ] Flutter Web build 通过
