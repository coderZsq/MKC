# 技术文档：[S3-7] Flutter AI 对话页面

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 级别：前端/移动端工程师
> 关联 PRD：[../prd/PRD_S3-7_flutter_chat_page.md](../prd/PRD_S3-7_flutter_chat_page.md)

---

## 1. 文档目标

定义 Flutter AI 对话页面的技术实现：页面结构、状态管理、SSE 消费、Markdown 渲染、引用卡片与测试策略。

---

## 2. 技术栈

- Flutter 3.22+
- Dart 3.4+
- flutter_riverpod 2.5.x
- dio 5.4.x
- flutter_markdown 0.7.x
- intl 0.19.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api/v1/conversations` | Bearer JWT | 会话列表 |
| POST | `/api/v1/conversations` | Bearer JWT | 创建会话 |
| GET | `/api/v1/conversations/{id}/messages` | Bearer JWT | 历史消息 |
| POST | `/api/v1/conversations/{id}/ask` | Bearer JWT | 提问 SSE |

---

## 4. 配置

无新增配置文件，使用现有 `lib/core/constants/api_constants.dart` 中的 baseUrl。

---

## 5. 模块设计

### 5.1 ChatPage

```dart
class ChatPage extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(chatProvider(conversationId));
    return Scaffold(
      appBar: ChatAppBar(title: state.title),
      body: MessageListView(messages: state.messages),
      bottomNavigationBar: ChatInputBar(
        onSend: (text) => ref.read(chatProvider(conversationId).notifier).send(text),
      ),
    );
  }
}
```

### 5.2 ChatNotifier

```dart
class ChatNotifier extends StateNotifier<ChatState> {
  ChatNotifier(this._chatRepository, this._sseClient) : super(ChatState.initial());

  Future<void> send(String text) async {
    state = state.copyWith(messages: [...state.messages, Message.user(text)]);
    final stream = _sseClient.ask(conversationId, text);
    final assistantMessage = Message.assistant(streaming: true);
    state = state.copyWith(messages: [...state.messages, assistantMessage]);

    await for (final event in stream) {
      if (event.type == 'chunk') {
        state = state.copyWith(
          messages: state.messages.map((m) => ...update).toList(),
        );
      } else if (event.type == 'citation') {
        ...
      } else if (event.type == 'done') {
        break;
      }
    }
  }
}
```

### 5.3 ChatSseClient

- 复用 S1-7 SSE 解析能力
- Web 端使用 `dart:html` EventSource
- 移动端使用 dio ResponseType.stream

---

## 6. 关键代码实现

### 6.1 流式消息气泡

```dart
class StreamingMessage extends StatelessWidget {
  final Message message;

  @override
  Widget build(BuildContext context) {
    return MarkdownMessage(
      content: message.content,
      citations: message.citations,
    );
  }
}
```

### 6.2 引用卡片

```dart
class CitationCard extends StatelessWidget {
  final Citation citation;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.go('/resources/${citation.resourceId}'),
      child: Chip(label: Text('${citation.resourceName} P${citation.page}')),
    );
  }
}
```

---

## 7. 错误映射

| 场景 | 处理方式 |
|---|---|
| SSE 连接失败 | 自动重连 5 次，失败后降级轮询 |
| 发送失败 | 显示 SnackBar 重试按钮 |
| 消息为空 | 禁用发送按钮 |
| 会话加载失败 | 显示错误页面与重试按钮 |

---

## 8. Web 端适配要点

- 使用 `flutter_markdown` 保证 Markdown 渲染一致
- Web 端 SSE 使用 `dart:html` EventSource
- 输入框适配浏览器键盘
- 引用卡片点击跳转至资源详情页或新标签页
- 使用 `flutter test --platform chrome` 测试

---

## 9. 测试策略

- **单元测试**：`ChatNotifier` 状态变化、SSE 事件解析
- **Widget 测试**：消息气泡、输入框、引用卡片渲染
- **集成测试**：真实会话 → 提问 → 验证流式答案

---

## 10. 检查清单

- [ ] `ChatPage` 页面与路由
- [ ] `ChatNotifier` 状态管理
- [ ] SSE 客户端与事件解析
- [ ] Markdown 渲染与引用卡片
- [ ] 多轮对话与历史消息加载
- [ ] 错误处理与重试
- [ ] Widget 测试覆盖率 80%+
- [ ] Web 端兼容性验证
- [ ] OpenAPI/文档同步更新
