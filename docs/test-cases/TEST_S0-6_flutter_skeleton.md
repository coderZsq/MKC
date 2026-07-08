# S0-6 测试用例：Flutter 项目骨架

## 1. 范围与目标

验证 `client/` 目录下 Flutter 项目已按 Clean Architecture 初始化，包含必需的依赖、目录、状态管理、路由、网络封装、主题、启动页与可运行的单元/Widget 测试。

## 2. 测试环境

- Flutter stable SDK 已安装
- 已执行 `flutter pub get`
- 可选：Android/iOS 模拟器或 `flutter test` 可直接运行

## 3. 测试用例

### 3.1 项目初始化与目录结构

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-001 | Functional | Static | P0 | `client/pubspec.yaml` 存在 | 仓库已克隆 | `ls client/pubspec.yaml` | 文件存在 | PRD AC-1 |
| MKC-TC-S0-6-002 | Functional | Static | P0 | `client/android/`、`client/ios/` 目录存在 | 仓库已克隆 | `ls -d client/android client/ios` | 目录存在 | PRD 推荐目录结构 |
| MKC-TC-S0-6-003 | Functional | Static | P0 | Clean Architecture 三层目录存在 | 仓库已克隆 | `ls -d client/lib/data client/lib/domain client/lib/presentation` | 三个目录均存在 | PRD AC-2 |
| MKC-TC-S0-6-004 | Functional | Static | P1 | `client/lib/config/` 包含环境、主题、常量配置 | 仓库已克隆 | `ls client/lib/config/` | 存在 env.dart / theme.dart / constants.dart 或等效文件 | PRD 推荐目录结构 |
| MKC-TC-S0-6-005 | Functional | Static | P1 | `client/lib/shared/` 包含错误处理与 Result 类型 | 仓库已克隆 | `ls client/lib/shared/` | 存在 errors/、result.dart 或等效文件 | PRD 推荐目录结构 |
| MKC-TC-S0-6-006 | Functional | Static | P1 | `client/test/` 目录存在 | 仓库已克隆 | `ls client/test/` | 目录存在且至少有一个测试文件 | PRD AC-9 |
| MKC-TC-S0-6-007 | Boundary | Static | P2 | 目录层级与 PRD 推荐结构一致 | 仓库已克隆 | `tree client/lib -L 3` | 关键路径 data/datasources/remote/、domain/entities/、presentation/pages/ 存在 | PRD 推荐目录结构 |

### 3.2 核心依赖

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-008 | Functional | Static | P0 | `pubspec.yaml` 声明 `flutter_riverpod` | 文件存在 | `grep "flutter_riverpod" client/pubspec.yaml` | 版本形如 `^2.5.x` | PRD 核心依赖 |
| MKC-TC-S0-6-009 | Functional | Static | P0 | `pubspec.yaml` 声明 `go_router` | 文件存在 | `grep "go_router" client/pubspec.yaml` | 版本形如 `^14.x` | PRD 核心依赖 |
| MKC-TC-S0-6-010 | Functional | Static | P0 | `pubspec.yaml` 声明 `dio` | 文件存在 | `grep "dio:" client/pubspec.yaml` | 版本形如 `^5.x` | PRD 核心依赖 |
| MKC-TC-S0-6-011 | Functional | Static | P1 | `pubspec.yaml` 声明 `freezed_annotation` 与 `json_annotation` | 文件存在 | `grep -E "freezed_annotation|json_annotation" client/pubspec.yaml` | 均存在且版本符合 PRD | PRD 核心依赖 |
| MKC-TC-S0-6-012 | Functional | Static | P1 | `pubspec.yaml` 声明 `flutter_secure_storage` | 文件存在 | `grep "flutter_secure_storage" client/pubspec.yaml` | 版本形如 `^9.x` | PRD 核心依赖 |
| MKC-TC-S0-6-013 | Functional | Static | P1 | dev_dependencies 包含 `build_runner`、`freezed`、`json_serializable`、`mockito`、`flutter_lints` | 文件存在 | `grep -E "build_runner|freezed:|json_serializable|mockito|flutter_lints" client/pubspec.yaml` | 均存在 | PRD 核心依赖 |

### 3.3 依赖安装与分析

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-014 | Functional | Integration | P0 | `flutter pub get` 成功 | 进入 client 目录 | `flutter pub get` | 无 fatal error，生成 `.dart_tool/` | PRD AC-1 |
| MKC-TC-S0-6-015 | Functional | Integration | P0 | `flutter analyze` 无错误 | 依赖已安装 | `flutter analyze` | 无 error，允许 info/warning | PRD AC-8 |
| MKC-TC-S0-6-016 | Negative | Integration | P1 | 存在 lint error 时 CI 失败 | 人为引入未使用变量 | `flutter analyze` | 返回非零退出码 | PRD AC-8 |
| MKC-TC-S0-6-017 | Functional | Integration | P0 | `flutter test` 可运行且至少一个测试通过 | 依赖已安装 | `flutter test` | 至少一个测试通过，无 crash | PRD AC-9 |

### 3.4 Clean Architecture 与状态管理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-018 | Functional | Static | P0 | domain 层不依赖 Flutter/Dart UI 包 | 文件存在 | 检查 `client/lib/domain/` 导入 | 无 `material.dart`、`widgets.dart` 导入 | PRD Clean Architecture |
| MKC-TC-S0-6-019 | Functional | Static | P1 | 存在 Riverpod Provider 或 StateNotifier | 文件存在 | `grep -R "StateNotifier\|StateProvider\|FutureProvider" client/lib/presentation/` | 至少存在一种 Riverpod 状态管理方式 | PRD AC-3 |
| MKC-TC-S0-6-020 | Functional | Unit | P1 | 示例 StateNotifier 状态机正常切换 | 代码存在 | 运行对应单元测试 | 状态可在 initial/loading/success/failure/empty 间切换 | PRD 状态管理约定 |
| MKC-TC-S0-6-021 | Functional | Static | P1 | Provider 按功能模块组织 | 文件存在 | `ls client/lib/presentation/providers/` | 存在 auth_provider.dart、upload_provider.dart 等或至少一个示例 | PRD 状态管理约定 |

### 3.5 路由与页面

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-022 | Functional | Static | P0 | 路由常量定义存在 | 文件存在 | `grep -R "splashRoute\|loginRoute\|homeRoute" client/lib/` | 存在 splashRoute、loginRoute、homeRoute 常量 | PRD 路由约定 |
| MKC-TC-S0-6-023 | Functional | Static | P1 | 使用 `go_router` 配置路由 | 文件存在 | `grep -R "GoRouter\|GoRoute" client/lib/` | 存在 GoRouter 实例与 GoRoute 列表 | PRD AC-4 |
| MKC-TC-S0-6-024 | Functional | Unit/Widget | P1 | 启动页 Splash Page 存在并可渲染 | 代码存在 | 运行 Splash widget 测试 | 页面渲染不抛出异常 | PRD AC-7 |
| MKC-TC-S0-6-025 | Functional | Widget | P1 | 空首页占位存在 | 代码存在 | 运行首页 widget 测试 | 页面包含占位文本或组件 | PRD AC-7 |
| MKC-TC-S0-6-026 | Functional | Widget | P2 | 路由跳转测试 | 代码存在 | 测试 `context.go('/login')` | 目标页面被 push | PRD 路由约定 |

### 3.6 网络层与 Token 存储

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-027 | Functional | Static | P0 | 存在 `ApiClient` 封装 | 文件存在 | `find client/lib -name "*api_client*" -o -name "*dio*"` | 存在 ApiClient 或 Dio 封装文件 | PRD 网络层约定 |
| MKC-TC-S0-6-028 | Functional | Static | P1 | `ApiClient` 统一解包后端响应信封 | 文件存在 | 阅读 ApiClient 代码 | 拦截器中将 `{success, data, error, meta}` 解包为 Result | PRD 网络层约定 |
| MKC-TC-S0-6-029 | Functional | Static | P1 | Token 刷新逻辑在拦截器中实现 | 文件存在 | 阅读 dio interceptor 代码 | 存在 401 自动刷新 access_token 并重试原请求的逻辑 | PRD 网络层约定 |
| MKC-TC-S0-6-030 | Functional | Unit | P1 | `ApiClient` 在 401 时触发刷新 | mock Dio | 单元测试模拟 401 + refresh 成功 | 请求重试并返回正确结果 | PRD 网络层约定 |
| MKC-TC-S0-6-031 | Functional | Static | P1 | 使用 `flutter_secure_storage` 存储 token | 文件存在 | `grep "FlutterSecureStorage" client/lib/` | 存在安全存储读写封装 | PRD 核心依赖 |
| MKC-TC-S0-6-032 | Security | Unit | P2 | Token 不存储在 SharedPreferences 等明文位置 | 代码存在 | 搜索 `SharedPreferences` 导入 | 无使用 SharedPreferences 存储 token | 安全基线 |

### 3.7 Result 类型与错误处理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-033 | Functional | Static | P0 | `Result<T, E>` 类型存在 | 文件存在 | `ls client/lib/shared/result.dart` | 文件存在 | PRD 推荐目录结构 |
| MKC-TC-S0-6-034 | Functional | Unit | P1 | `Result.success` 与 `Result.failure` 可正确创建 | 代码存在 | 运行 Result 单元测试 | success 承载数据，failure 承载错误 | PRD 推荐目录结构 |
| MKC-TC-S0-6-035 | Functional | Static | P1 | 存在自定义 `AppException` 层级 | 文件存在 | `ls client/lib/shared/errors/` | 存在 AppException / ServerException / NetworkException 等 | PRD 推荐目录结构 |
| MKC-TC-S0-6-036 | Functional | Unit | P2 | 错误对象可映射为用户友好消息 | 代码存在 | 运行异常映射测试 | `NetworkException` 映射为 "网络连接失败" 等 | PRD 技术要点 |

### 3.8 主题与环境

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-037 | Functional | Static | P1 | 环境配置区分 dev/prod | 文件存在 | 阅读 `client/lib/config/env.dart` | 存在 dev/prod baseUrl 切换逻辑 | PRD AC-6 |
| MKC-TC-S0-6-038 | Functional | Static | P1 | 基础主题配置存在 | 文件存在 | 阅读 `client/lib/config/theme.dart` | 定义 `ThemeData` 或 `MaterialColor` | PRD AC-6 |
| MKC-TC-S0-6-039 | Functional | Widget | P2 | 应用可启动并显示主题色 | 代码存在 | 运行 `flutter run` 或 widget 测试 | 启动页渲染无异常，主题色生效 | PRD AC-6 |

### 3.9 异常、边界与兼容性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-6-040 | Exception | Unit | P1 | 网络超时返回 failure 而非抛异常 | mock Dio | 测试 connectTimeout 场景 | `Result.failure(NetworkException)` | PRD 网络层约定 |
| MKC-TC-S0-6-041 | Boundary | Unit | P2 | 超长响应体不会导致 UI 卡死 | 模拟大 JSON | 测试 ApiClient 解析 | 异步处理，结果正确返回 | 工程最佳实践 |
| MKC-TC-S0-6-042 | Compatibility | Integration | P2 | 项目在 iOS / Android / Web 分析均通过 | 依赖已安装 | `flutter analyze` 针对各平台 | 无平台相关错误（Web 可选） | PRD 备注 |
| MKC-TC-S0-6-043 | Idempotency | Integration | P2 | 重复运行 `flutter test` 结果一致 | 测试已通过 | 连续运行 3 次 | 结果一致 | 工程最佳实践 |
| MKC-TC-S0-6-044 | Performance | Integration | P2 | `flutter build apk --debug` 成功 | 依赖已安装 | 运行构建命令 | 生成 APK 文件，无编译错误 | PRD 工作流设计 |

## 4. 测试执行清单

- [ ] `client/` 目录结构符合 Clean Architecture
- [ ] 核心依赖版本符合 PRD
- [ ] `flutter analyze` 无 error
- [ ] `flutter test` 至少一个测试通过
- [ ] Riverpod / go_router / dio / flutter_secure_storage 已集成
- [ ] Result 类型与 AppException 层级存在且通过单元测试
- [ ] README 说明项目结构与启动命令

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
