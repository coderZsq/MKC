# 技术文档：[S1-2] Flutter 登录/注册页面设计

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 级别：移动端/Web 端工程师  
> 关联 PRD：[PRD_S1-2_flutter_auth_pages.md](../prd/PRD_S1-2_flutter_auth_pages.md)

---

## 1. 文档目标

定义 Flutter 客户端认证模块的 UI 结构、数据模型、状态流转、网络层封装与测试方案，为 S1-2 编码提供可直接落地的蓝图。

---

## 2. 技术栈

- Flutter 3.22+
- Dart 3.4+
- flutter_riverpod 2.5
- dio 5.4
- go_router 14.1
- flutter_secure_storage 9.2
- freezed 2.5

## 2.1 Web 端适配要点

- `TokenProvider` 是一个平台无关的抽象接口，实际实现由 S0-6 骨架提供。移动端使用 `flutter_secure_storage`，Web 端使用其 web 实现（localStorage），接口调用完全一致。
- Web 端 Dio 请求受浏览器 CORS 限制，要求 Gateway 在 S1-1 中配置允许 Flutter Web 启动地址（如 `http://localhost:12345`）的跨域头。
- Web 端无法直接调起系统键盘，需保证所有输入框可通过 Tab 聚焦、Enter 提交，并兼容鼠标/触摸操作。
- 集成测试在 Web 端使用 ChromeDriver；单元/Widget 测试可通过 `flutter test --platform chrome` 运行。

---

## 3. 数据模型

### 3.1 Token 模型

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'auth_token_model.freezed.dart';
part 'auth_token_model.g.dart';

@freezed
class AuthTokenModel with _$AuthTokenModel {
  const factory AuthTokenModel({
    @JsonKey(name: 'access_token') required String accessToken,
    @JsonKey(name: 'refresh_token') required String refreshToken,
    @JsonKey(name: 'expires_in') required int expiresIn,
    @JsonKey(name: 'token_type') required String tokenType,
  }) = _AuthTokenModel;

  factory AuthTokenModel.fromJson(Map<String, dynamic> json) =>
      _$AuthTokenModelFromJson(json);
}
```

### 3.2 请求模型

```dart
@freezed
class LoginRequestModel with _$LoginRequestModel {
  const factory LoginRequestModel({
    required String email,
    required String password,
  }) = _LoginRequestModel;

  factory LoginRequestModel.fromJson(Map<String, dynamic> json) =>
      _$LoginRequestModelFromJson(json);
}

@freezed
class RegisterRequestModel with _$RegisterRequestModel {
  const factory RegisterRequestModel({
    required String email,
    required String password,
    String? nickname,
  }) = _RegisterRequestModel;

  factory RegisterRequestModel.fromJson(Map<String, dynamic> json) =>
      _$RegisterRequestModelFromJson(json);
}
```

---

## 4. 网络层

### 4.1 AuthApi

```dart
class AuthApi {
  AuthApi({required ApiClient client}) : _client = client;

  final ApiClient _client;

  Future<Result<AuthTokenModel>> login(LoginRequestModel req) async {
    return _client.post<AuthTokenModel>(
      '/auth/login',
      data: req.toJson(),
      parser: (data) => AuthTokenModel.fromJson(data as Map<String, dynamic>),
    );
  }

  Future<Result<AuthTokenModel>> register(RegisterRequestModel req) async {
    return _client.post<AuthTokenModel>(
      '/auth/register',
      data: req.toJson(),
      parser: (data) => AuthTokenModel.fromJson(data as Map<String, dynamic>),
    );
  }
}
```

### 4.2 AuthRepository

```dart
class AuthRepository {
  AuthRepository({
    required AuthApi authApi,
    required TokenProvider tokenProvider,
  })  : _authApi = authApi,
        _tokenProvider = tokenProvider;

  final AuthApi _authApi;
  final TokenProvider _tokenProvider;

  Future<Result<void>> login({required String email, required String password}) async {
    final result = await _authApi.login(
      LoginRequestModel(email: email, password: password),
    );
    return result.map(_persistTokens);
  }

  Future<Result<void>> register({
    required String email,
    required String password,
    String? nickname,
  }) async {
    final result = await _authApi.register(
      RegisterRequestModel(email: email, password: password, nickname: nickname),
    );
    return result.map(_persistTokens);
  }

  Future<void> logout() => _tokenProvider.clearTokens();

  Future<bool> isAuthenticated() async {
    final token = await _tokenProvider.getAccessToken();
    return token != null && token.isNotEmpty;
  }

  Future<void> _persistTokens(AuthTokenModel tokens) async {
    await _tokenProvider.setTokens(
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
    );
  }
}
```

---

## 5. 状态管理

```dart
@freezed
class AuthState with _$AuthState {
  const factory AuthState({
    @Default(false) bool isLoading,
    @Default(false) bool isAuthenticated,
    @Default(AuthScreenStatus.unknown) AuthScreenStatus status,
    AppException? error,
  }) = _AuthState;
}

enum AuthScreenStatus { unknown, authenticated, unauthenticated }

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier({required AuthRepository repo}) : _repo = repo, super(const AuthState());

  final AuthRepository _repo;

  Future<void> checkAuthentication() async {
    state = state.copyWith(isLoading: true, error: null);
    final isAuth = await _repo.isAuthenticated();
    state = state.copyWith(
      isLoading: false,
      isAuthenticated: isAuth,
      status: isAuth ? AuthScreenStatus.authenticated : AuthScreenStatus.unauthenticated,
    );
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repo.login(email: email, password: password);
    state = result.fold(
      (_) => state.copyWith(isLoading: false, isAuthenticated: true, status: AuthScreenStatus.authenticated, error: null),
      (err) => state.copyWith(isLoading: false, isAuthenticated: false, error: err),
    );
  }

  Future<void> register(String email, String password, {String? nickname}) async {
    state = state.copyWith(isLoading: true, error: null);
    final result = await _repo.register(email: email, password: password, nickname: nickname);
    state = result.fold(
      (_) => state.copyWith(isLoading: false, isAuthenticated: true, status: AuthScreenStatus.authenticated, error: null),
      (err) => state.copyWith(isLoading: false, isAuthenticated: false, error: err),
    );
  }

  void clearError() => state = state.copyWith(error: null);
}
```

Provider 定义：

```dart
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final api = AuthApi(client: ref.watch(apiClientProvider));
  final storage = ref.watch(tokenStorageProvider);
  return AuthRepository(authApi: api, tokenProvider: storage);
});

final authNotifierProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(repo: ref.watch(authRepositoryProvider)),
);
```

---

## 6. 路由配置

```dart
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authNotifierProvider);

  return GoRouter(
    initialLocation: splashRoute,
    redirect: (context, state) {
      final status = authState.status;
      final path = state.uri.path;

      if (status == AuthScreenStatus.unknown) {
        return splashRoute;
      }
      if (status == AuthScreenStatus.authenticated) {
        if (path == loginRoute || path == registerRoute) return homeRoute;
        return null;
      }
      // unauthenticated
      if (path == loginRoute || path == registerRoute) return null;
      return loginRoute;
    },
    routes: [
      GoRoute(path: splashRoute, builder: (_, __) => const SplashPage()),
      GoRoute(path: loginRoute, builder: (_, __) => const LoginPage()),
      GoRoute(path: registerRoute, builder: (_, __) => const RegisterPage()),
      GoRoute(path: homeRoute, builder: (_, __) => const HomePage()),
    ],
  );
});
```

---

## 7. UI 页面

### 7.1 LoginPage

- 顶部应用 Logo + 名称
- 邮箱输入框（`TextFormField`, `keyboardType: TextInputType.emailAddress`）
- 密码输入框（`obscureText: true`）
- 登录按钮（带 loading 状态）
- “还没有账号？去注册” 文本按钮
- 错误提示：`if (state.error != null) Text(..., style: errorStyle)`

### 7.2 RegisterPage

- 邮箱/密码/确认密码/昵称（可选）输入框
- 注册按钮
- 表单校验实时或提交时触发
- “已有账号？去登录” 文本按钮

### 7.3 表单校验函数

```dart
String? validateEmail(String? value) {
  if (value == null || value.isEmpty) return '请输入邮箱';
  if (!EmailValidator.validate(value)) return '邮箱格式不正确';
  return null;
}

String? validatePassword(String? value) {
  if (value == null || value.length < 8) return '密码至少 8 位';
  if (!RegExp(r'(?=.*[A-Za-z])(?=.*\d)').hasMatch(value)) return '密码需同时包含字母和数字';
  return null;
}
```

---

## 8. 错误映射

| 异常类型 | 显示文案 |
|---|---|
| `NetworkException` | 网络异常，请检查连接 |
| `UnauthorizedException` | 邮箱或密码错误 |
| `ServerException(code: 'CONFLICT')` | 邮箱已被注册 |
| 其他 `ServerException` | 服务繁忙，请稍后重试 |
| `UnknownException` | 发生未知错误，请重试 |

---

## 9. 测试策略

- **单元测试**：AuthRepository mock AuthApi + TokenProvider
- **Widget 测试**：LoginPage 校验错误、加载状态、成功跳转；使用 `flutter test --platform chrome` 验证 Web 渲染
- **集成测试**：完整启动 → Splash → 登录 → 首页（Android/iOS/Web 任选其一）

---

## 10. 检查清单

- [ ] `LoginPage` / `RegisterPage` 页面实现
- [ ] 表单校验函数与错误提示
- [ ] `AuthApi` / `AuthRepository` 网络封装
- [ ] `AuthNotifier` 状态管理与导航触发
- [ ] `AppRouter` 基于认证状态重定向
- [ ] `TokenProvider` 写入 token（移动端安全存储 / Web localStorage）
- [ ] Widget 测试与集成测试（含 Web 平台验证）
- [ ] `flutter analyze` 0 issues
