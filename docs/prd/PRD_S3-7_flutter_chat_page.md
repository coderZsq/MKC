# PRD：[S3-7] Flutter AI 对话页面

> 版本：v1.0
> 日期：2026-07-10
> 作者：朱双泉
> 关联文档：[PRD_S1-6_flutter_task_center.md](./PRD_S1-6_flutter_task_center.md)、[PRD_S1-7_task_progress_push.md](./PRD_S1-7_task_progress_push.md)、[PRD_S3-6_sse_qa_api.md](./PRD_S3-6_sse_qa_api.md)、[PRD_S3-8_conversation_persistence.md](./PRD_S3-8_conversation_persistence.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S3-7 |
| **任务名称** | Flutter AI 对话页面 |
| **所属史诗** | E7 AI 对话 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S3-6 SSE 问答 API |
| **目标 Sprint** | Sprint 3 |

---

## 描述

作为用户，我希望在 iOS、Android 或 Web（Chrome）端与知识库进行多轮对话，能够输入问题、实时看到流式生成的答案、查看历史消息并跳转到相关资源。本任务在 Flutter 端实现 AI 对话页面，复用 S1-7 的 SSE 客户端能力，接入 S3-6 的问答 SSE 接口，并支持 Markdown 渲染与引用来源展示。

---

## 验收标准（AC）

- [ ] **AC-1** Flutter 提供 `ChatPage`，展示消息列表（用户问题与 AI 回答）
- [ ] **AC-2** 用户输入问题后，立即创建消息气泡并调用 S3-6 SSE 问答接口
- [ ] **AC-3** AI 回答以流式方式逐字显示，支持打字机效果
- [ ] **AC-4** 答案使用 Markdown 渲染，支持代码块、列表、加粗等格式
- [ ] **AC-5** 答案中的引用来源以可点击卡片展示，显示资源名称与页码/时间戳
- [ ] **AC-6** 支持多轮对话，历史消息随会话 ID 持久化（S3-8）
- [ ] **AC-7** 支持新建会话、切换会话、删除会话
- [ ] **AC-8** 加载失败时显示重试按钮，并支持取消正在生成的回答
- [ ] **AC-9** 单元/Widget 测试覆盖率 80%+，Web 端使用 `flutter test --platform chrome`

---

## 推荐目录结构

```
client/lib/
├── presentation/
│   ├── pages/
│   │   ├── chat_page.dart
│   │   └── conversation_list_page.dart
│   ├── widgets/
│   │   ├── chat_bubble.dart
│   │   ├── chat_input_bar.dart
│   │   ├── streaming_message.dart
│   │   ├── citation_card.dart
│   │   └── markdown_message.dart
│   ├── notifiers/
│   │   ├── chat_notifier.dart
│   │   └── conversation_list_notifier.dart
│   └── providers/
│       ├── chat_provider.dart
│       └── conversation_list_provider.dart
├── domain/
│   ├── models/
│   │   ├── message.dart
│   │   ├── conversation.dart
│   │   └── citation.dart
│   └── repositories/
│       ├── chat_repository.dart
│       └── conversation_repository.dart
└── data/
    └── datasources/
        ├── chat_remote_datasource.dart
        └── chat_sse_client.dart
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| flutter_riverpod | 2.5.x | 状态管理 |
| dio | 5.4.x | SSE 流式读取 |
| flutter_markdown | 0.7.x | Markdown 渲染 |
| flutter_animate | 4.x | 打字机动画（可选） |
| intl | 0.19.x | 时间格式化 |

---

## 技术要点

### 消息模型

```dart
class Message {
  final String id;
  final String conversationId;
  final MessageRole role;        // user / assistant
  final String content;
  final List<Citation> citations;
  final DateTime createdAt;
  final bool isStreaming;
}

class Citation {
  final String resourceId;
  final String resourceName;
  final String? page;
  final Duration? timestamp;
  final double score;
}
```

### 流式消息处理

- 收到 `chunk` 事件时追加到当前 assistant 消息内容
- 收到 `citation` 事件时追加到当前消息的引用列表
- 收到 `done` 时标记 `isStreaming = false`
- 收到 `error` 时显示错误提示并停止流式

### 客户端行为

- 页面进入时加载历史消息
- 输入框发送后禁用输入直到生成完成或取消
- 点击引用卡片跳转至 S2-7 内容查看页（或 Web 新标签页）
- 离开页面时取消未完成的 SSE 订阅

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Markdown 渲染性能差 | 长答案卡顿 | 使用 ListView + 懒加载 |
| 流式消息状态管理复杂 | UI 不同步 | 使用 Riverpod 管理单一会话的 message 状态 |
| Web 端 SSE 兼容性 | 流式中断 | 使用原生 EventSource + 轮询降级 |

---

## Web 端适配

- 使用 `flutter_markdown` 保证 Web 端渲染一致
- Web 端 SSE 使用 `dart:html` 原生 `EventSource` 或 `eventsource` 包
- 消息输入框需要适配浏览器软键盘与回车发送
- 引用卡片点击在 Web 端打开资源详情页或新标签页
- 使用 `flutter test --platform chrome` 验证 Widget 渲染与事件处理

---

## 备注

- 对话页初始版本支持单会话内多轮对话，S4 可引入 Agent 工作流增强
- 需要与 S3-8 的会话模型保持一致，会话标题可自动取第一问题的前 20 字
- 建议将 SSE 订阅逻辑抽象为 `ChatSseClient`，便于复用 S1-7 的解析能力
