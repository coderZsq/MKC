# PRD：[S1-2] 实现 Flutter 登录/注册页面

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 关联文档：[PRD_S1-1_user_auth_api.md](./PRD_S1-1_user_auth_api.md)、[TECH_S1-2_flutter_auth_pages.md](../tech/TECH_S1-2_flutter_auth_pages.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S1-2 |
| **任务名称** | 实现 Flutter 登录/注册页面 |
| **所属史诗** | E1 用户认证 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S1-1 用户注册/登录 API、S0-6 Flutter 骨架 |
| **目标 Sprint** | Sprint 1 |

---

## 描述

作为用户，我需要在 iOS、Android 或 Web（Chrome）端登录或注册账号，才能进入应用主界面并管理我的知识库资源。本任务在 Flutter 客户端实现跨平台登录/注册 UI、表单校验、状态管理与 token 持久化，并与 S1-1 的认证 API 完成端到端联调。

---

## 验收标准（AC）

- [ ] **AC-1** 提供 `LoginPage` 与 `RegisterPage`，支持邮箱/密码输入，切换登录/注册模式
- [ ] **AC-2** 表单本地校验：邮箱格式、密码长度≥8、密码包含字母和数字、注册时确认密码一致
- [ ] **AC-3** 点击提交调用 S1-1 API，失败时显示服务端错误文案
- [ ] **AC-4** 登录/注册成功后持久化 access_token 与 refresh_token，并跳转首页
- [ ] **AC-5** 启动页（SplashPage）自动检测本地 token，已登录则跳转首页，未登录则跳转登录页
- [ ] **AC-6** 登录/注册流程在 Web（Chrome）端可正常运行：token 写入持久化、跳转首页、401 时重定向登录页
- [ ] **AC-7** 所有状态变化使用 Riverpod 管理，UI 只负责展示与触发事件
- [ ] **AC-8** Widget 测试覆盖提交成功/失败/校验错误分支
- [ ] **AC-9** 集成测试覆盖完整登录 → 首页导航流程，并在 Android/iOS/Web(Chrome) 至少一个平台验证通过

---

## 推荐目录结构

```
client/lib/
├── data/
│   ├── datasources/
│   │   ├── remote/
│   │   │   └── auth_api.dart            # /auth/* 接口封装
│   │   └── secure/
│   │       └── secure_token_storage.dart # 已存在，复用
│   ├── models/
│   │   ├── auth_token_model.dart
│   │   ├── login_request_model.dart
│   │   └── register_request_model.dart
│   └── repositories/
│       └── auth_repository.dart
├── domain/
│   ├── repositories/
│   │   └── token_provider.dart           # 已存在，复用
│   └── entities/
│       └── user.dart
├── presentation/
│   ├── pages/
│   │   ├── splash_page.dart              # 已存在，改造自动跳转
│   │   ├── login_page.dart
│   │   └── register_page.dart
│   ├── providers/
│   │   └── auth_provider.dart            # 已存在，扩展业务方法
│   └── routes/
│       └── app_router.dart               # 基于 auth 状态的重定向
└── main.dart                             # ProviderScope
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| flutter_riverpod | ^2.5.1 | 状态管理 |
| dio | ^5.4.3 | HTTP 请求 |
| go_router | ^14.1.4 | 路由与重定向 |
| flutter_secure_storage | ^9.2.2 | Token 安全存储 |
| freezed | ^2.5.2 | 不可变数据模型 |

---

## 技术要点

### 状态管理

- `AuthNotifier` 持有 `AuthState`（`isLoading`、`isAuthenticated`、`error`）。
- 提供 `login(email, password)`、`register(...)`、`checkStoredToken()` 方法。
- UI 通过 `ConsumerWidget`/`Consumer` 监听状态并触发加载、错误提示、导航。

### 表单校验

- 邮箱：合法邮箱正则
- 密码：长度≥8，同时包含字母和数字
- 注册：确认密码必须与密码一致
- 提交前校验，任一字段非法即禁用按钮并提示

### 导航与重定向

- `AppRouter` 使用 `redirect`：
  - 初始化时 `AuthNotifier` 正在检查 token → 停留 Splash
  - 已认证 → 跳转 `homeRoute`
  - 未认证且不在登录/注册页 → 跳转 `loginRoute`
- 登录页提供“去注册”链接，注册页提供“去登录”链接

### 错误处理

- 网络错误：`NetworkException` → 显示“网络异常，请检查连接”
- 401/403：`UnauthorizedException` → 显示“邮箱或密码错误”
- 409：`ServerException(code: 'CONFLICT')` → 显示“邮箱已被注册”
- 服务端未知错误：显示兜底文案“服务繁忙，请稍后重试”

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| S1-1 API 尚未完成 | 无法真机联调 | 先使用 mock repository 编写 UI/状态；S1-1 完成后替换 |
| flutter_secure_storage 在部分平台实现差异（桌面/Web 使用 localStorage） | 集成测试失败 | 测试注入 mock TokenProvider；Web 端可接受 localStorage 方案，后续如需更高安全性再替换 |
| 键盘弹出导致布局溢出 | 低端设备 UI 异常 | 所有表单页使用 `SingleChildScrollView` + `SafeArea` |

---

## Web 端适配

- 登录/注册页面需使用 `LayoutBuilder` / `ConstrainedBox` 保证在 Chrome 桌面与移动视口下均能正常显示。
- Token 持久化在 Web 端依赖 `flutter_secure_storage` 的 web 实现（基于 localStorage），本次 Sprint 可接受；后续若需更高安全性，可替换为加密后的 localStorage 方案。
- Web 端 Dio 请求受浏览器 CORS 限制，要求 S1-1 Gateway 配置允许 Flutter Web 域名的跨域头。
- Web 端集成测试使用 `flutter test --platform chrome`（Widget/单元）或 ChromeDriver（集成测试）。

---

## 备注

- 本任务不实现“忘记密码”、“第三方登录”、“验证码登录”
- 头像/昵称字段在注册页为可选，优先保证最小可用登录流程
- 登录成功后如需获取用户信息，可调用 `/api/v1/auth/me` 或延后到首页加载
