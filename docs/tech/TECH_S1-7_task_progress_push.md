# 技术文档：[S1-7] SSE 任务进度实时推送设计

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 级别：后端/移动端/Web 端工程师  
> 关联 PRD：[PRD_S1-7_task_progress_push.md](../prd/PRD_S1-7_task_progress_push.md)

---

## 1. 文档目标

定义 Gateway SSE 实时推送通道与 Flutter 客户端订阅消费的完整实现方案，包括接口契约、订阅广播机制、连接生命周期、降级策略与测试方案。

---

## 2. 技术栈

### Gateway

- Go 1.22+
- Gin 1.10.x
- 标准库 `context`、`sync`

### Flutter

- Flutter 3.22+
- Dart 3.4+
- dio 5.4
- flutter_riverpod 2.5
- eventsource (Web 可选) / dart:html `EventSource`

## 2.1 Web 端适配要点

- Web 端浏览器 `EventSource` 无法设置 `Authorization` 头，JWT 必须通过 `?token=` 查询参数传递；Gateway auth 中间件同时解析 Header 与 Query。
- Gateway SSE 端点需配置 CORS：允许的 origin、允许 `text/event-stream` Content-Type、允许查询参数。
- Web 端 Flutter 客户端使用条件导入或 platform check：
  - Web：通过 `EventSource` 监听 `progress`/`status`/`done`/`error` 事件，解析 `event.data`。
  - 移动端/桌面端：使用 dio `ResponseType.stream` 读取字节流并解析 SSE。
- Web 端 SSE 断线后同样执行重连与轮询降级，最多 5 次重试。
- Web 端测试使用 `flutter test --platform chrome` 验证解析与状态更新；集成测试使用 ChromeDriver。

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api/v1/tasks/{task_id}/events` | Bearer JWT | SSE 流式推送任务事件 |

### 请求示例

```text
GET /api/v1/tasks/01922b9c-.../events
Authorization: Bearer <access_token>
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### 响应头

```text
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### 事件示例

**progress**

```text
event: progress
data: {"task_id":"01922b9c-...","progress":35,"status":"running","message":null,"timestamp":"2026-07-08T10:05:00Z"}

```

**status**

```text
event: status
data: {"task_id":"01922b9c-...","progress":0,"status":"running","message":null,"timestamp":"2026-07-08T10:01:00Z"}

```

**done**

```text
event: done
data: {"task_id":"01922b9c-...","progress":100,"status":"completed","message":null,"timestamp":"2026-07-08T10:10:00Z"}

```

**error**

```text
event: error
data: {"task_id":"01922b9c-...","progress":0,"status":"failed","message":"解析失败","timestamp":"2026-07-08T10:10:00Z"}

```

---

## 4. Gateway 设计

### 4.1 SSE Event 结构

```go
type TaskEvent struct {
    EventID   string          `json:"-"`
    EventType string          `json:"-"`
    TaskID    string          `json:"task_id"`
    Progress  uint8           `json:"progress"`
    Status    string          `json:"status"`
    Message   *string         `json:"message"`
    Timestamp time.Time       `json:"timestamp"`
}

func (e TaskEvent) ToSSE() string {
    data, _ := json.Marshal(e)
    return fmt.Sprintf("event: %s\ndata: %s\n\n", e.EventType, data)
}
```

### 4.2 订阅广播器

```go
type TaskBroadcaster interface {
    Subscribe(ctx context.Context, taskID string) (<-chan TaskEvent, error)
    Publish(ctx context.Context, taskID string, event TaskEvent)
    Close(taskID string)
}

type inMemoryTaskBroadcaster struct {
    mu    sync.RWMutex
    subs  map[string][]chan TaskEvent
}

func (b *inMemoryTaskBroadcaster) Subscribe(ctx context.Context, taskID string) (<-chan TaskEvent, error) {
    ch := make(chan TaskEvent, 1)
    b.mu.Lock()
    b.subs[taskID] = append(b.subs[taskID], ch)
    b.mu.Unlock()

    go func() {
        <-ctx.Done()
        b.mu.Lock()
        defer b.mu.Unlock()
        subs := b.subs[taskID]
        for i, c := range subs {
            if c == ch {
                b.subs[taskID] = append(subs[:i], subs[i+1:]...)
                close(ch)
                break
            }
        }
    }()

    return ch, nil
}

func (b *inMemoryTaskBroadcaster) Publish(ctx context.Context, taskID string, event TaskEvent) {
    b.mu.RLock()
    subs := b.subs[taskID]
    b.mu.RUnlock()
    for _, ch := range subs {
        select {
        case ch <- event:
        case <-ctx.Done():
            return
        }
    }
}
```

### 4.3 SSE Handler

```go
func (h *TaskSSEHandler) Stream(c *gin.Context) {
    userID := c.GetUint64("user_id")
    taskUUID := c.Param("task_id")

    task, err := h.taskSvc.Get(c.Request.Context(), userID, taskUUID)
    if err != nil {
        handleServiceError(c, err)
        return
    }

    c.Header("Content-Type", "text/event-stream; charset=utf-8")
    c.Header("Cache-Control", "no-cache")
    c.Header("Connection", "keep-alive")
    c.Header("X-Accel-Buffering", "no")
    c.Status(http.StatusOK)

    flusher, ok := c.Writer.(http.Flusher)
    if !ok {
        return
    }

    ctx, cancel := context.WithCancel(c.Request.Context())
    defer cancel()

    ch, _ := h.broadcaster.Subscribe(ctx, taskUUID)

    // 发送当前状态作为 initial 事件
    fmt.Fprint(c.Writer, TaskEvent{
        EventType: "status",
        TaskID:    task.ID,
        Progress:  task.Progress,
        Status:    task.Status,
        Timestamp: time.Now().UTC(),
    }.ToSSE())
    flusher.Flush()

    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case event, ok := <-ch:
            if !ok {
                return
            }
            fmt.Fprint(c.Writer, event.ToSSE())
            flusher.Flush()
            if event.Status == model.TaskStatusCompleted || event.Status == model.TaskStatusFailed {
                return
            }
        case <-ticker.C:
            fmt.Fprint(c.Writer, "event: heartbeat\ndata: {}\n\n")
            flusher.Flush()
        case <-ctx.Done():
            return
        }
    }
}
```

### 4.4 状态变更触发广播

在 `TaskService` 的状态推进方法中调用 `broadcaster.Publish`：

```go
func (s *taskService) MarkRunning(ctx context.Context, taskUUID string) error {
    // ... 状态机校验与更新 ...
    s.broadcaster.Publish(ctx, taskUUID, TaskEvent{
        EventType: "status",
        TaskID:    taskUUID,
        Progress:  0,
        Status:    model.TaskStatusRunning,
        Timestamp: time.Now().UTC(),
    })
    return nil
}
```

---

## 5. Flutter 设计

### 5.1 SSE Parser

```dart
class SseEvent {
  const SseEvent({required this.event, required this.data});

  final String event;
  final Map<String, dynamic> data;
}

Stream<SseEvent> parseSseStream(Stream<List<int>> byteStream) {
  final buffer = StringBuffer();
  return byteStream
      .transform(utf8.decoder)
      .expand((chunk) => chunk.split('\n'))
      .map((line) {
    if (line.startsWith('event: ')) {
      return _PendingEvent(event: line.substring(7));
    } else if (line.startsWith('data: ')) {
      return _PendingData(data: line.substring(6));
    } else if (line.trim().isEmpty) {
      return const _EventComplete();
    }
    return const _SseIgnore();
  })
      .scan(...); // 组合 event 与 data，最终产出 SseEvent
}
```

### 5.2 TaskSSEClient

```dart
class TaskSseClient {
  TaskSseClient({required Dio dio}) : _dio = dio;

  final Dio _dio;
  CancelToken? _cancelToken;

  Stream<TaskProgressEvent> listen(String taskId, {String? token}) {
    _cancelToken = CancelToken();
    final queryParameters = token != null ? {'token': token} : null;
    final response = _dio.get<ResponseBody>(
      '/tasks/$taskId/events',
      queryParameters: queryParameters,
      options: Options(responseType: ResponseType.stream, headers: {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      }),
      cancelToken: _cancelToken,
    );

    return response
        .asStream()
        .asyncExpand((r) => parseSseStream(r.data!.stream))
        .map((e) => TaskProgressEvent.fromJson(e.data));
  }

  void dispose() {
    _cancelToken?.cancel('dispose');
  }
}
```

### 5.3 Web SSE 客户端

Web 端使用浏览器 `EventSource`，通过查询参数携带 token：

```dart
import 'dart:html' as html;
import 'package:flutter/foundation.dart';

Stream<TaskProgressEvent> listenWebSse(String taskId, {required String token}) {
  final eventSource = html.EventSource('/api/v1/tasks/$taskId/events?token=$token');

  final controller = StreamController<TaskProgressEvent>(onCancel: () {
    eventSource.close();
  });

  void onMessage(String type) {
    eventSource.addEventListener(type, (html.Event event) {
      final data = (event as html.MessageEvent).data as String?;
      if (data == null) return;
      try {
        final json = jsonDecode(data) as Map<String, dynamic>;
        controller.add(TaskProgressEvent.fromJson(json));
      } catch (_) {
        // 解析失败忽略或记录日志
      }
    });
  }

  onMessage('progress');
  onMessage('status');
  onMessage('done');
  onMessage('error');

  eventSource.onError.listen((_) => controller.addError(Object()));

  return controller.stream;
}
```

### 5.4 平台选择封装

```dart
Stream<TaskProgressEvent> listenTaskSse({
  required String taskId,
  required String token,
  required Dio dio,
}) {
  if (kIsWeb) {
    return listenWebSse(taskId, token: token);
  }
  return TaskSseClient(dio: dio).listen(taskId, token: token);
}
```

### 5.5 任务中心集成

在 `TaskCenterNotifier` 或页面中为 running 任务启动 SSE：

```dart
void subscribeToTask(String taskId) {
  _sseSubscription = _sseClient.listen(taskId).listen(
    (event) {
      _updateTaskInState(event);
    },
    onError: (_) {
      _startPollingFallback(taskId);
    },
    onDone: () {
      _stopPolling();
    },
  );
}
```

### 5.6 降级轮询

```dart
void _startPollingFallback(String taskId) {
  _pollTimer?.cancel();
  _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
    final result = await _repo.getTask(taskId);
    result.fold(
      (task) => _updateTaskInState(task),
      (_) {},
    );
    if (task?.status != TaskStatus.running) {
      _pollTimer?.cancel();
    }
  });
}
```

---

## 6. 错误处理

| 场景 | HTTP 状态 | 处理 |
|---|---|---|
| 任务不存在或无权访问 | 404 | 不建立 SSE 连接 |
| token 无效 | 401 | 返回标准 envelope 错误 |
| 客户端断开 | - | 清理订阅，无错误 |
| 广播器 channel 满 | - | 丢弃事件，避免阻塞 |

---

## 7. 测试策略

### Gateway

- **单元测试**：`TaskBroadcaster` 订阅/发布/清理逻辑
- **集成测试**：httptest 模拟 SSE 连接，验证事件格式、heartbeat、断开清理
- **接口测试**：401/404、认证参数兼容

### Flutter

- **单元测试**：`parseSseStream` 解析、Web SSE 事件映射
- **Widget 测试**：任务 running 时进度随 SSE 更新；Web 端使用 mock `EventSource` 或平台通道
- **集成测试**：真实上传文件 → 订阅 SSE → 验证进度变化（Web 端使用 ChromeDriver）

---

## 8. 检查清单

- [ ] `TaskEvent` 结构与 SSE 序列化
- [ ] `TaskBroadcaster` 内存订阅管理
- [ ] `GET /tasks/{id}/events` SSE handler
- [ ] 状态推进方法中调用 Publish
- [ ] 客户端 SSE 流解析（移动端 dio / Web EventSource）
- [ ] 客户端自动重连与轮询降级
- [ ] 页面离开时取消订阅
- [ ] Gateway/Flutter 单元与集成测试（含 Web 平台验证）
- [ ] OpenAPI 文档同步更新
