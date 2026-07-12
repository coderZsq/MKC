# 技术文档：[S4-3] 资源卡片展示摘要与标签

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 级别：前端/移动端工程师
> 关联 PRD：[../prd/PRD_S4-3_resource_card_summary_tag.md](../prd/PRD_S4-3_resource_card_summary_tag.md)

---

## 1. 文档目标

定义资源列表卡片展示摘要与标签的技术实现：数据模型、网络层、状态管理、Widget 结构（`ResourceSummaryText`、`TagChipRow`）、标签过滤交互、错误映射与测试策略，为 S4-3 编码提供可直接落地的蓝图。

---

## 2. 技术栈

- Flutter 3.22+
- Dart 3.4+
- flutter_riverpod 2.5.x
- dio 5.4.x
- go_router 14.x
- freezed 2.5.x
- intl 0.19.x

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/api/v1/resources` | Bearer JWT | 资源列表（含 summary、tags） |
| GET | `/api/v1/resources?tag={tag}` | Bearer JWT | 按标签过滤资源列表 |
| GET | `/api/v1/resources?page={n}&limit={m}` | Bearer JWT | 分页加载 |

### 请求示例

```http
GET /api/v1/resources?page=1&limit=20&tag=周会 HTTP/1.1
Authorization: Bearer <jwt>
```

### 响应示例

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "resource_id": "res_001",
        "name": "产品周会-20260701.mp3",
        "type": "audio",
        "status": "completed",
        "summary": "本次周会讨论了 Q3 路线图，确认语音助手与 PDF 智能抽取为优先级最高的两项能力。",
        "summary_truncated": false,
        "tags": ["周会", "Q3规划", "路线图"],
        "updated_at": "2026-07-12T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

### 错误码

| HTTP 状态码 | code | 含义 | 客户端处理 |
|---|---|---|---|
| 400 | 40001 | 参数错误（tag 非法） | 提示“筛选参数无效”，清除筛选 |
| 401 | 40100 | 未登录/Token 失效 | 跳转登录页 |
| 404 | 40400 | 资源不存在 | 显示空状态 |
| 500 | 50000 | 服务异常 | 显示错误提示与重试按钮 |

---

## 4. 配置

无新增配置文件，使用现有 `lib/config/constants.dart` 中的 baseUrl；标签筛选最大长度限制 `maxTagLength = 32`，列表分页 `defaultLimit = 20`。

---

## 5. 模块设计

### 5.1 ResourceListPage

```dart
class ResourceListPage extends ConsumerWidget {
  const ResourceListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(resourceListNotifierProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('资源库')),
      body: Column(
        children: [
          if (state.selectedTag != null)
            ActiveTagFilterBar(
              tag: state.selectedTag!,
              onClear: () =>
                  ref.read(resourceListNotifierProvider.notifier).clearFilter(),
            ),
          Expanded(
            child: state.when(
              loading: () => const ResourceListSkeleton(),
              error: (e, _) => ErrorBanner(
                message: '加载失败，请重试',
                onRetry: () =>
                    ref.read(resourceListNotifierProvider.notifier).refresh(),
              ),
              data: (data) => data.items.isEmpty
                  ? const EmptyResourceView()
                  : ResourceListView(items: data.items, hasMore: data.hasMore),
            ),
          ),
        ],
      ),
    );
  }
}
```

### 5.2 ResourceListNotifier

```dart
class ResourceListNotifier
    extends FamilyAsyncNotifier<ResourceListState, String?> {
  static const _limit = 20;

  @override
  Future<ResourceListState> build(String? tag) async {
    final repo = ref.read(resourceRepositoryProvider);
    final result = await repo.fetchResources(page: 1, limit: _limit, tag: tag);
    return result.fold(
      (items) => ResourceListState(
        items: items,
        currentPage: 1,
        hasMore: items.length == _limit,
        selectedTag: tag,
      ),
      (error) => throw error,
    );
  }

  String? get selectedTag => arg;

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => _loadPage(1));
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || !current.hasMore || current.isLoadingMore) return;
    state = AsyncData(current.copyWith(isLoadingMore: true));
    final nextPage = current.currentPage + 1;
    final repo = ref.read(resourceRepositoryProvider);
    final result =
        await repo.fetchResources(page: nextPage, limit: _limit, tag: arg);
    state = result.fold(
      (items) => AsyncData(current.copyWith(
        items: [...current.items, ...items],
        currentPage: nextPage,
        hasMore: items.length == _limit,
        isLoadingMore: false,
      )),
      (error) => AsyncData(current.copyWith(
        error: error,
        isLoadingMore: false,
      )),
    );
  }

  Future<void> filterByTag(String tag) async {
    state = const AsyncLoading();
    final repo = ref.read(resourceRepositoryProvider);
    final result = await repo.fetchResources(page: 1, limit: _limit, tag: tag);
    state = result.fold(
      (items) => AsyncData(ResourceListState(
        items: items,
        currentPage: 1,
        hasMore: items.length == _limit,
        selectedTag: tag,
      )),
      (error) => AsyncData(ResourceListState(
        items: const [],
        selectedTag: tag,
        error: error,
      )),
    );
  }

  Future<void> clearFilter() async {
    state = const AsyncLoading();
    final repo = ref.read(resourceRepositoryProvider);
    final result = await repo.fetchResources(page: 1, limit: _limit, tag: null);
    state = result.fold(
      (items) => AsyncData(ResourceListState(
        items: items,
        currentPage: 1,
        hasMore: items.length == _limit,
        selectedTag: null,
      )),
      (error) => throw error,
    );
  }
}
```

> 说明：使用 `FamilyAsyncNotifier` 以 `selectedTag` 为 family 参数，切换标签时通过 `ref.invalidate(resourceListNotifierProvider(tag))` 重建，保证状态不可变（每次 `copyWith` 生成新对象）。

### 5.3 ResourceRepository

```dart
abstract class ResourceRepository {
  Future<Result<List<Resource>>> fetchResources({
    required int page,
    required int limit,
    String? tag,
  });
}

class ResourceRepositoryImpl implements ResourceRepository {
  ResourceRepositoryImpl({required ResourceApi api}) : _api = api;

  final ResourceApi _api;

  @override
  Future<Result<List<Resource>>> fetchResources({
    required int page,
    required int limit,
    String? tag,
  }) async {
    if (tag != null && tag.trim().isEmpty) {
      return Result.failure(const ValidationException('标签不能为空'));
    }
    if (tag != null && tag.length > 32) {
      return Result.failure(const ValidationException('标签长度超限'));
    }
    final result = await _api.fetchResources(page: page, limit: limit, tag: tag);
    return result.map((models) => models.map(_toEntity).toList());
  }

  Resource _toEntity(ResourceModel m) => Resource(
        id: m.resourceId,
        name: m.name,
        type: m.type,
        status: m.status,
        summary: m.summary,
        summaryTruncated: m.summaryTruncated,
        tags: List<String>.unmodifiable(m.tags),
        updatedAt: DateTime.parse(m.updatedAt),
      );
}
```

### 5.4 ResourceCard Widget

```dart
class ResourceCard extends ConsumerWidget {
  const ResourceCard({required this.resource, super.key});

  final Resource resource;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: () => context.push('/resources/${resource.id}/content'),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      resource.name,
                      style: Theme.of(context).textTheme.titleMedium,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  ResourceStatusChip(status: resource.status),
                ],
              ),
              const SizedBox(height: 8),
              ResourceSummaryText(
                summary: resource.summary,
                truncated: resource.summaryTruncated,
              ),
              const SizedBox(height: 8),
              TagChipRow(
                tags: resource.tags,
                onTagTap: (tag) => ref
                    .read(resourceListNotifierProvider(null).notifier)
                    .filterByTag(tag),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

## 6. 关键代码实现

### 6.1 ResourceSummaryText（折叠/展开）

```dart
class ResourceSummaryText extends StatefulWidget {
  const ResourceSummaryText({
    required this.summary,
    required this.truncated,
    super.key,
  });

  final String? summary;
  final bool truncated;

  @override
  State<ResourceSummaryText> createState() => _ResourceSummaryTextState();
}

class _ResourceSummaryTextState extends State<ResourceSummaryText> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final summary = widget.summary;
    if (summary == null || summary.trim().isEmpty) {
      return Text('暂无摘要',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          summary,
          maxLines: _expanded ? null : 2,
          overflow: _expanded ? TextOverflow.visible : TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => setState(() => _expanded = !_expanded),
            child: Text(_expanded ? '收起' : '展开'),
          ),
        ),
      ],
    );
  }
}
```

### 6.2 TagChipRow（横向滚动 + 标签过滤）

```dart
class TagChipRow extends StatelessWidget {
  const TagChipRow({
    required this.tags,
    required this.onTagTap,
    super.key,
  });

  final List<String> tags;
  final ValueChanged<String> onTagTap;

  @override
  Widget build(BuildContext context) {
    if (tags.isEmpty) {
      return Text('暂无标签',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ));
    }
    return SizedBox(
      height: 32,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final tag in tags) ...[
              ActionChip(
                label: Text(tag),
                onPressed: () => onTagTap(tag),
                visualDensity: VisualDensity.compact,
              ),
              const SizedBox(width: 8),
            ],
          ],
        ),
      ),
    );
  }
}
```

### 6.3 ResourceModel（data 层）

```dart
@freezed
class ResourceModel with _$ResourceModel {
  const factory ResourceModel({
    @JsonKey(name: 'resource_id') required String resourceId,
    required String name,
    required String type,
    required String status,
    String? summary,
    @JsonKey(name: 'summary_truncated') @Default(false) bool summaryTruncated,
    @Default([]) List<String> tags,
    @JsonKey(name: 'updated_at') required String updatedAt,
  }) = _ResourceModel;

  factory ResourceModel.fromJson(Map<String, dynamic> json) =>
      _$ResourceModelFromJson(json);
}
```

### 6.4 ResourceApi

```dart
class ResourceApi {
  ResourceApi({required Dio dio}) : _dio = dio;

  final Dio _dio;

  Future<Result<List<ResourceModel>>> fetchResources({
    required int page,
    required int limit,
    String? tag,
  }) async {
    try {
      final response = await _dio.get<dynamic>(
        '/api/v1/resources',
        queryParameters: {
          'page': page,
          'limit': limit,
          if (tag != null) 'tag': tag,
        },
      );
      final body = response.data as Map<String, dynamic>;
      final data = body['data'] as Map<String, dynamic>;
      final items = (data['items'] as List<dynamic>)
          .cast<Map<String, dynamic>>()
          .map(ResourceModel.fromJson)
          .toList();
      return Result.success(items);
    } on DioException catch (e) {
      return Result.failure(_mapDioException(e));
    }
  }
}
```

---

## 7. 错误映射

| 场景 | 异常/状态码 | UI 反馈 |
|---|---|---|
| 网络断开 | DioExceptionType.connectionError | “网络异常，请检查连接” + 重试 |
| 401 | UnauthorizedException | 跳转登录页 |
| 400（tag 非法） | ValidationException | “筛选参数无效”，清除筛选 |
| 404 | ResourceNotFoundException | 显示空状态“暂无资源” |
| 500 | ServerException | “加载失败，请稍后重试” + 重试 |
| summary 为 null/空 | - | 显示“暂无摘要”占位 |
| tags 为空 | - | 显示“暂无标签”占位 |
| 筛选结果为空 | - | 显示“无匹配资源” + 清除筛选 |

---

## 8. Web 端适配要点

- 卡片使用 `LayoutBuilder`，宽屏（>=720）限制最大宽度并居中
- `TagChipRow` 使用 `SingleChildScrollView(scrollDirection: Axis.horizontal)`，Web 端鼠标可拖拽滚动；Chip 不换行，避免撑高卡片
- ActionChip 在 Web 端点击事件需通过 `flutter test --platform chrome` 验证
- Web 端 Dio 受 CORS 限制，Gateway 需配置允许 Flutter Web 域名的跨域头
- 折叠/展开按钮在 Web 端使用鼠标点击，无需适配软键盘
- 单元/Widget 测试使用 `flutter test --platform chrome`；集成测试使用 ChromeDriver

---

## 9. 测试策略

- **单元测试**：`ResourceRepositoryImpl` 的 `_toEntity` 映射、tag 校验（空/超长）、`ResourceListNotifier` 的 `filterByTag`/`clearFilter`/`loadMore` 状态转换
- **Widget 测试**：`ResourceSummaryText` 折叠/展开切换、空摘要占位；`TagChipRow` 横向滚动、点击触发回调、空标签占位；`ResourceCard` 整体渲染与点击跳转；空状态与错误状态 UI
- **集成测试**：真实登录 -> 进入资源列表 -> 点击标签筛选 -> 清除筛选（Web 端使用 ChromeDriver）
- **覆盖率**：`flutter test --coverage`，目标 80%+

---

## 10. 检查清单

- [ ] `ResourceModel`、`Resource` 实体定义（含 summary、tags）
- [ ] `ResourceApi` 与 `ResourceRepositoryImpl` 实现（含 tag 校验）
- [ ] `ResourceListNotifier` 状态管理（family + immutable copyWith）
- [ ] `ResourceListPage` 页面实现（含筛选条、空/错误状态）
- [ ] `ResourceCard`、`ResourceSummaryText`、`TagChipRow` 组件实现
- [ ] 摘要折叠/展开交互
- [ ] 标签 Chip 横向滚动与点击过滤
- [ ] 清除筛选恢复全量列表
- [ ] 未登录跳转
- [ ] Widget 与集成测试（含 `flutter test --platform chrome`）
- [ ] 测试覆盖率 80%+
- [ ] `flutter analyze` 0 issues
- [ ] OpenAPI/文档同步更新
