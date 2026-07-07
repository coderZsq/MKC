# 技术文档：[S0-6] Flutter 项目骨架与架构设计

> 版本：v1.0  
> 日期：2026-07-06  > 作者：朱双泉  > 级别：架构师/移动端负责人  > 关联 PRD：[PRD_S0-6_flutter_project_skeleton.md](../prd/PRD_S0-6_flutter_project_skeleton.md)

---

## 1. 文档目标

本文档定义 MKC 项目 Flutter 客户端的架构设计、目录结构、状态管理方案、路由设计、网络层封装、依赖注入、错误处理策略以及开发规范。

---

## 2. 架构选型

### 2.1 Clean Architecture 分层

```
lib/
├── main.dart
├── app.dart
├── config/                 # 配置层
├── data/                   # 数据层
│   ├── datasources/        # 远程/本地数据源
│   ├── models/             # DTO/数据模型
│   └── repositories/       # 仓库实现
├── domain/                 # 领域层
│   ├── entities/           # 纯业务实体
│   ├── repositories/       # 仓库接口
│   └── usecases/           # 用例
├── presentation/           # 表现层
│   ├── pages/              # 页面
│   ├── widgets/            # 可复用组件
│   ├── providers/          # Riverpod Provider
│   └── state/              # StateNotifier 状态类
└── shared/                 # 共享工具
    ├── constants/
    ├── errors/
    ├── extensions/
    └── utils/
```

### 2.2 依赖方向

```
presentation ──▶ domain ◀── data
                    ▲
                    └── shared
```

外层依赖内层，内层不依赖外层。

---

## 3. 状态管理方案

### 3.1 Riverpod + StateNotifier

| 层级 | 组件 | 用途 |
|---|---|---|
| Provider | 依赖注入和全局状态读取 | `StateNotifierProvider` |
| StateNotifier | 业务状态 + 操作 | 一个页面/功能一个 Notifier |
| State | 不可变状态对象 | 使用 `freezed` 生成 |

### 3.2 状态类示例

```dart
@freezed
class AuthState with _$AuthState {
  const factory AuthState({
    @Default(false) bool isLoading,
    User? user,
    AppException? error,
  }) = _AuthState;
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._loginUseCase) : super(const AuthState());

  final LoginUseCase _loginUseCase;

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _loginUseCase(email, password);
    result.fold(
      (error) => state = state.copyWith(isLoading: false, error: error),
      (user) => state = state.copyWith(isLoading: false, user: user),
    );
  }
}
```

### 3.3 Provider 组织

```dart
// providers.dart
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRepositoryImpl(apiClient);
});

final loginUseCaseProvider = Provider<LoginUseCase>((ref) {
  final repo = ref.watch(authRepositoryProvider);
  return LoginUseCase(repo);
});

final authNotifierProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final useCase = ref.watch(loginUseCaseProvider);
  return AuthNotifier(useCase);
});
```

---

## 4. 路由设计

### 4.1 使用 go_router

```dart
final router = GoRouter(
  initialLocation: '/splash',
  redirect: (context, state) {
    final isLoggedIn = ref.read(authNotifierProvider).user != null;
    if (!isLoggedIn && state.uri.path != '/login') return '/login';
    return null;
  },
  routes: [
    GoRoute(path: '/splash', builder: (_, __) => const SplashPage()),
    GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
    GoRoute(path: '/', builder: (_, __) => const HomePage()),
    GoRoute(path: '/resources', builder: (_, __) => const ResourcesPage()),
    GoRoute(path: '/conversation/:id', builder: (_, state) => ConversationPage(id: state.pathParameters['id']!)),
  ],
);
```

### 4.2 路由表

| 路径 | 页面 | 权限 |
|---|---|---|
| /splash | 启动页 | 无 |
| /login | 登录/注册 | 未登录 |
| / | 首页/仪表盘 | 登录 |
| /resources | 资源列表 | 登录 |
| /resource/:id | 资源详情 | 登录 |
| /conversation/:id | 对话详情 | 登录 |
| /settings | 设置 | 登录 |

---

## 5. 网络层封装

### 5.1 dio 配置

```dart
class ApiClient {
  ApiClient({required this.baseUrl, required this.tokenProvider}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));

    _dio.interceptors.add(_authInterceptor());
    _dio.interceptors.add(LogInterceptor(responseBody: true));
  }

  late final Dio _dio;
  final String baseUrl;
  final TokenProvider tokenProvider;

  Interceptor _authInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await tokenProvider.getAccessToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        options.headers['X-Request-ID'] = const Uuid().v4();
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await tokenProvider.refreshAccessToken();
          if (refreshed) {
            final token = await tokenProvider.getAccessToken();
            error.requestOptions.headers['Authorization'] = 'Bearer $token';
            return handler.resolve(await _dio.fetch(error.requestOptions));
          }
        }
        handler.next(error);
      },
    );
  }
}
```

### 5.2 Result 类型

```dart
@freezed
class Result<T> with _$Result<T> {
  const factory Result.success(T data) = Success<T>;
  const factory Result.failure(AppException error) = Failure<T>;
}
```

---

## 6. Token 管理

### 6.1 本地存储

- `access_token`：内存中（Riverpod State）
- `refresh_token`：Secure Storage（flutter_secure_storage）

### 6.2 TokenProvider 接口

```dart
abstract class TokenProvider {
  Future<String?> getAccessToken();
  Future<bool> refreshAccessToken();
  Future<void> clearTokens();
}
```

---

## 7. 错误处理

### 7.1 AppException 层级

```dart
@freezed
class AppException with _$AppException {
  const factory AppException.network() = NetworkException;
  const factory AppException.server({String? code, String? message}) = ServerException;
  const factory AppException.unauthorized() = UnauthorizedException;
  const factory AppException.validation(Map<String, String> errors) = ValidationException;
}
```

### 7.2 UI 层统一处理

```dart
ref.listen(authNotifierProvider, (previous, next) {
  if (next.error != null) {
    ErrorDialog.show(context, next.error!);
  }
});
```

---

## 8. 依赖列表

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_localizations:
    sdk: flutter

  # 状态管理
  flutter_riverpod: ^2.5.1
  riverpod_annotation: ^2.3.5

  # 路由
  go_router: ^14.1.4

  # 网络
  dio: ^5.4.3

  # 本地存储
  flutter_secure_storage: ^9.2.2
  shared_preferences: ^2.2.3

  # 模型生成
  freezed_annotation: ^2.4.1
  json_annotation: ^4.9.0
  uuid: ^4.4.0

  # UI
  flutter_screenutil: ^5.9.3
  shimmer: ^3.0.0

  # 文件选择/上传
  file_picker: ^8.0.5

  # 国际化
  intl: ^0.19.0

dev_dependencies:
  build_runner: ^2.4.11
  freezed: ^2.5.2
  json_serializable: ^6.8.0
  riverpod_generator: ^2.4.0
  flutter_lints: ^4.0.0
```

---

## 9. 开发规范

### 9.1 命名约定

| 类型 | 命名 | 示例 |
|---|---|---|
| 页面 | `XxxPage` | `LoginPage` |
| Notifier | `XxxNotifier` | `AuthNotifier` |
| State | `XxxState` | `AuthState` |
| UseCase | `XxxUseCase` | `LoginUseCase` |
| Repository | `XxxRepository` | `AuthRepository` |
| DTO | `XxxModel` | `UserModel` |
| Entity | `Xxx` | `User` |

### 9.2 文件大小限制

- 单个文件 < 400 行
- Widget 拆分到最小可复用单元
- UseCase 单一职责

---

## 10. 检查清单

- [ ] Flutter 项目创建成功
- [ ] Clean Architecture 目录结构建立
- [ ] Riverpod + StateNotifier 示例实现
- [ ] go_router 路由配置完成
- [ ] dio 网络层封装 + Token 刷新
- [ ] flutter_secure_storage 集成
- [ ] freezed 模型生成跑通
- [ ] 登录页骨架实现
- [ ] CI 通过 flutter analyze + flutter test
- [ ] README 说明启动和目录
