# 技术文档：[S1-6] Flutter 任务中心页面设计

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 级别：移动端/Web 端工程师  
> 关联 PRD：[PRD_S1-6_flutter_task_center.md](../prd/PRD_S1-6_flutter_task_center.md)

---

## 1. 文档目标

定义 Flutter 任务中心页面的数据模型、网络层、状态管理、UI 结构与测试方案，为 S1-6 编码提供可直接落地的蓝图。

---

## 2. 技术栈

- Flutter 3.22+
- Dart 3.4+
- flutter_riverpod 2.5
- dio 5.4
- go_router 14
- freezed 2.5
- intl 0.19

## 2.1 Web 端适配要点

- 列表布局使用 `LayoutBuilder` / `ConstrainedBox` 适配桌面与移动视口；宽屏可限制最大宽度并居中。
- Web 端下拉刷新：保持 `RefreshIndicator` 可用，同时提供显式刷新按钮兼容鼠标操作。
- Web 端滚动加载更多通过 `ScrollController` 实现，同时提供“加载更多”按钮作为降级方案。
- Web 端 SSE 进度推送由 S1-7 统一封装；任务中心监听任务进度事件并局部更新对应任务状态，避免整页刷新。
- 单元/Widget 测试使用 `flutter test --platform chrome`；集成测试使用 ChromeDriver。

---

## 3. 数据模型

### 3.1 TaskModel（data 层）

```dart
@freezed
class TaskModel with _$TaskModel {
  const factory TaskModel({
    @JsonKey(name: 'task_id') required String taskId,
    @JsonKey(name: 'resource_id') required String resourceId,
    @JsonKey(name: 'resource_name') required String resourceName,
    required String type,
    required String status,
    required int progress,
    @JsonKey(name: 'error_message') String? errorMessage,
    @JsonKey(name: 'updated_at') required String updatedAt,
  }) = _TaskModel;

  factory TaskModel.fromJson(Map<String, dynamic> json) =>
      _$TaskModelFromJson(json);
}
```

### 3.2 TaskEntity（domain 层）

```dart
@freezed
class Task with _$Task {
  const factory Task({
    required String id,
    required String resourceId,
    required String resourceName,
    required TaskType type,
    required TaskStatus status,
    required int progress,
    String? errorMessage,
    required DateTime updatedAt,
  }) = _Task;
}

enum TaskStatus { pending, running, completed, failed }

enum TaskType { mediaParse, pdfParse, documentParse }
```

### 3.3 TaskCenterState

```dart
@freezed
class TaskCenterState with _$TaskCenterState {
  const factory TaskCenterState({
    @Default([]) List<Task> tasks,
    @Default(1) int currentPage,
    @Default(false) bool hasMore,
    @Default(false) bool isLoadingMore,
    AppException? error,
  }) = _TaskCenterState;
}
```

---

## 4. 网络层

### 4.1 TaskApi

```dart
class TaskApi {
  TaskApi({required Dio dio}) : _dio = dio;

  final Dio _dio;

  Future<Result<List<TaskModel>>> fetchTasks({
    required int page,
    required int limit,
  }) async {
    try {
      final response = await _dio.get<dynamic>(
        '/tasks',
        queryParameters: {'page': page, 'limit': limit},
      );
      final body = response.data as Map<String, dynamic>;
      final data = body['data'] as List<dynamic>;
      final tasks = data
          .cast<Map<String, dynamic>>()
          .map(TaskModel.fromJson)
          .toList();
      return Result.success(tasks);
    } on DioException catch (e) {
      return Result.failure(_mapDioException(e));
    }
  }
}
```

### 4.2 TaskRepository

```dart
class TaskRepositoryImpl implements TaskRepository {
  TaskRepositoryImpl({required TaskApi api}) : _api = api;

  final TaskApi _api;

  @override
  Future<Result<List<Task>>> fetchTasks({int page = 1, int limit = 20}) async {
    final result = await _api.fetchTasks(page: page, limit: limit);
    return result.map(
      (models) => models.map(_mapToEntity).toList(),
    );
  }

  Task _mapToEntity(TaskModel model) => Task(
        id: model.taskId,
        resourceId: model.resourceId,
        resourceName: model.resourceName,
        type: _parseTaskType(model.type),
        status: _parseTaskStatus(model.status),
        progress: model.progress,
        errorMessage: model.errorMessage,
        updatedAt: DateTime.parse(model.updatedAt),
      );
}
```

---

## 5. 状态管理

```dart
class TaskCenterNotifier extends AsyncNotifier<TaskCenterState> {
  TaskCenterNotifier() : super();

  late final TaskRepository _repo;
  static const _limit = 20;

  @override
  Future<TaskCenterState> build() async {
    _repo = ref.read(taskRepositoryProvider);
    final result = await _repo.fetchTasks(page: 1, limit: _limit);
    return result.fold(
      (tasks) => TaskCenterState(
        tasks: tasks,
        currentPage: 1,
        hasMore: tasks.length == _limit,
      ),
      (error) => TaskCenterState(error: error),
    );
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => _loadPage(1));
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || current.isLoadingMore || !current.hasMore) return;

    state = AsyncData(current.copyWith(isLoadingMore: true));
    final nextPage = current.currentPage + 1;
    final result = await _repo.fetchTasks(page: nextPage, limit: _limit);

    state = result.fold(
      (tasks) => AsyncData(
        current.copyWith(
          tasks: [...current.tasks, ...tasks],
          currentPage: nextPage,
          hasMore: tasks.length == _limit,
          isLoadingMore: false,
        ),
      ),
      (error) => AsyncData(
        current.copyWith(
          error: error,
          isLoadingMore: false,
        ),
      ),
    );
  }
}
```

Provider 定义：

```dart
final taskRepositoryProvider = Provider<TaskRepository>((ref) {
  return TaskRepositoryImpl(api: TaskApi(dio: ref.watch(dioProvider)));
});

final taskCenterNotifierProvider =
    AsyncNotifierProvider<TaskCenterNotifier, TaskCenterState>(
  TaskCenterNotifier.new,
);
```

---

## 6. UI 页面

### 6.1 TaskCenterPage

- `AppBar` 标题“任务中心”
- `RefreshIndicator` 包裹 `ListView.builder`
- `ListView.builder` 展示任务项
- 底部：`isLoadingMore ? LinearProgressIndicator : const SizedBox.shrink()`
- 空状态：`Center` 显示图标 + “暂无任务” + “去上传”按钮
- 错误状态：`Center` 显示错误文案 + 重试按钮

### 6.2 TaskListItem

```dart
class TaskListItem extends StatelessWidget {
  const TaskListItem({required this.task, super.key});

  final Task task;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: _TypeIcon(task.type),
      title: Text(task.resourceName, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TaskStatusChip(status: task.status),
          if (task.status == TaskStatus.running)
            LinearProgressIndicator(value: task.progress / 100),
          Text('更新于 ${_formatTime(task.updatedAt)}'),
        ],
      ),
      onTap: () => context.push('/tasks/${task.id}'),
    );
  }
}
```

### 6.3 TaskStatusChip

```dart
class TaskStatusChip extends StatelessWidget {
  const TaskStatusChip({required this.status, super.key});

  final TaskStatus status;

  Color get _color {
    switch (status) {
      case TaskStatus.pending: return Colors.grey;
      case TaskStatus.running: return Colors.blue;
      case TaskStatus.completed: return Colors.green;
      case TaskStatus.failed: return Colors.red;
    }
  }

  String get _label {
    switch (status) {
      case TaskStatus.pending: return '等待中';
      case TaskStatus.running: return '处理中';
      case TaskStatus.completed: return '已完成';
      case TaskStatus.failed: return '失败';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(_label, style: const TextStyle(color: Colors.white)),
      backgroundColor: _color,
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }
}
```

---

## 7. 路由与导航

在 `app_routes.dart` 增加：

```dart
static const String taskCenter = '/tasks';
static const String taskDetail = '/tasks/:id';
```

页面映射：

```dart
GoRoute(
  path: AppRoutes.taskCenter,
  builder: (_, __) => const TaskCenterPage(),
),
GoRoute(
  path: AppRoutes.taskDetail,
  builder: (_, state) => TaskDetailPage(taskId: state.pathParameters['id']!),
),
```

未登录拦截由 `AuthProvider` 在路由守卫中处理。

---

## 8. 错误处理

| 场景 | 异常/状态码 | UI 反馈 |
|---|---|---|
| 网络断开 | DioExceptionType.connectionError | “网络异常，请检查连接” + 重试 |
| 401 | UnauthorizedException | 跳转登录页 |
| 500 | ServerException | “加载失败，请稍后重试” + 重试 |
| 列表为空 | - | “暂无任务” + 去上传 |

---

## 9. 测试策略

- **单元测试**：`_parseTaskStatus`、`_formatTime`、状态机转换
- **Widget 测试**：列表渲染、下拉刷新触发 `refresh()`、滚动到底部触发 `loadMore()`、空状态与错误状态 UI；使用 `flutter test --platform chrome` 验证 Web 渲染
- **集成测试**：真实登录 → 上传文件 → 任务中心出现任务（Web 端使用 ChromeDriver）

---

## 10. 检查清单

- [ ] `TaskModel`、`TaskEntity`、`TaskCenterState` 定义
- [ ] `TaskApi` 与 `TaskRepository` 实现
- [ ] `TaskCenterNotifier` 分页状态管理
- [ ] `TaskCenterPage` 页面实现（含 Web 响应式布局）
- [ ] `TaskListItem`、`TaskStatusChip` 组件实现
- [ ] 下拉刷新与上拉加载更多（Web 端提供显式按钮降级）
- [ ] 空状态与错误状态 UI
- [ ] 未登录跳转
- [ ] Widget 与集成测试（含 Web 平台验证）
- [ ] `flutter analyze` 0 issues
