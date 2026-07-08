# S1-2 测试用例：Flutter 登录/注册页面

## 1. 范围与目标

验证 Flutter 客户端登录/注册模块的 UI 校验、状态管理、网络调用、token 持久化与导航行为符合 PRD/TECH 要求。

## 2. 测试环境

- Flutter 3.22+
- Dart 3.4+
- Android/iOS 模拟器、桌面端或 Chrome（Web）
- S1-1 API 已启动（集成测试），或已配置 mock 接口（单元/widget 测试）
- `flutter pub get` 已执行
- Web 测试：`flutter test --platform chrome`；集成测试需 ChromeDriver

## 3. 测试用例

### 3.1 表单校验

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-2-001 | Functional | Widget | P0 | 空邮箱提交显示必填提示 | 在登录页 | 清空邮箱，点击登录 | 邮箱输入框下方显示“请输入邮箱” | PRD AC-2 |
| MKC-TC-S1-2-002 | Functional | Widget | P0 | 非法邮箱格式提示 | 在登录页 | 输入 `not-email` | 显示“邮箱格式不正确” | PRD AC-2 |
| MKC-TC-S1-2-003 | Functional | Widget | P0 | 密码过短提示 | 在登录页 | 输入 5 位密码 | 显示“密码至少 8 位” | PRD AC-2 |
| MKC-TC-S1-2-004 | Functional | Widget | P0 | 密码缺少字母或数字提示 | 在登录页 | 输入纯数字密码 | 显示“密码需同时包含字母和数字” | PRD AC-2 |
| MKC-TC-S1-2-005 | Functional | Widget | P0 | 注册页确认密码不一致提示 | 在注册页 | 密码 `Passw0rd!`，确认密码 `Password1!` | 显示“两次输入的密码不一致” | PRD AC-2 |

### 3.2 登录流程

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-2-006 | Functional | Widget | P0 | 合法登录跳转首页 | API 返回 200 | 输入正确邮箱密码点击登录 | 按钮出现 loading，随后导航到首页 | PRD AC-4 |
| MKC-TC-S1-2-007 | Functional | Unit | P1 | 登录成功后持久化 token | mock repository | 调用 login | TokenProvider 写入 access/refresh token | PRD AC-4 |
| MKC-TC-S1-2-008 | Negative | Widget | P0 | 错误密码显示服务端错误 | API 返回 401 | 输入错误密码 | 显示“邮箱或密码错误”，不跳转 | PRD AC-3 |
| MKC-TC-S1-2-009 | Negative | Widget | P1 | 网络错误显示网络异常 | 无网络 | 点击登录 | 显示“网络异常，请检查连接” | PRD 错误处理 |

### 3.3 注册流程

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-2-010 | Functional | Widget | P0 | 合法注册跳转首页 | API 返回 200 | 输入正确信息点击注册 | 导航到首页 | PRD AC-4 |
| MKC-TC-S1-2-011 | Negative | Widget | P0 | 重复邮箱显示已被注册 | API 返回 409 | 用已存在邮箱注册 | 显示“邮箱已被注册” | PRD AC-3 |
| MKC-TC-S1-2-012 | Functional | Unit | P1 | 注册成功后持久化 token | mock repository | 调用 register | TokenProvider 写入 token | PRD AC-4 |

### 3.4 启动与导航

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-2-013 | Functional | Integration | P0 | 已登录用户启动直达首页 | SecureStorage 存有 token | 启动 App | Splash 后进入首页 | PRD AC-5 |
| MKC-TC-S1-2-014 | Functional | Integration | P0 | 未登录用户启动进入登录页 | 无 token | 启动 App | Splash 后进入登录页 | PRD AC-5 |
| MKC-TC-S1-2-015 | Functional | Widget | P1 | 登录页可跳转注册页 | 在登录页 | 点击“去注册” | 进入 RegisterPage | PRD AC-1 |
| MKC-TC-S1-2-016 | Functional | Widget | P1 | 注册页可跳转登录页 | 在注册页 | 点击“去登录” | 进入 LoginPage | PRD AC-1 |
| MKC-TC-S1-2-017 | Security | Integration | P1 | token 失效后重定向登录 | 存储过期 access_token，refresh 也失败 | 启动 App | 被重定向到登录页 | TECH 路由 |

### 3.5 状态管理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-2-018 | Functional | Unit | P0 | AuthNotifier login 成功切换状态 | mock repo | 调用 login | state.isAuthenticated=true, isLoading=false, error=null | TECH 5 |
| MKC-TC-S1-2-019 | Functional | Unit | P0 | AuthNotifier login 失败保留错误 | mock repo 返回错误 | 调用 login | state.error 不为 null，isAuthenticated=false | TECH 5 |
| MKC-TC-S1-2-020 | Functional | Unit | P1 | clearError 清除错误 | 存在 error | 调用 clearError | state.error == null | TECH 5 |

### 3.6 代码质量与可访问性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-2-021 | Functional | Static | P1 | `flutter analyze` 无错误 | 代码存在 | 运行 `flutter analyze` | 0 issues | 工程规范 |
| MKC-TC-S1-2-022 | Functional | Static | P1 | 无硬编码 API URL 或密钥 | 代码存在 | 全局搜索 `http://`、`password=` | 仅 Env 与测试文件出现 | 安全基线 |
| MKC-TC-S1-2-023 | Accessibility | Widget | P2 | 表单字段语义标签正确 | 页面存在 | 检查 TextFormField 的 `labelText`/`hintText` | 屏幕阅读器可识别 | 可访问性 |
| MKC-TC-S1-2-024 | Functional | Integration | P1 | 登录页软键盘不遮挡提交按钮 | 页面存在 | 聚焦密码输入框 | 使用 `SingleChildScrollView` 可滚动到底部 | PRD 阻塞风险 |

### 3.7 Web 与跨平台兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-2-025 | Compatibility | Widget | P1 | 登录页在 Chrome 正常渲染 | 代码存在 | `flutter test --platform chrome` | 测试通过，无渲染异常 | PRD Web AC |
| MKC-TC-S1-2-026 | Compatibility | Unit | P1 | Web 端 token 持久化使用同一接口 | mock TokenProvider | 调用 setTokens | 不依赖 `dart:io` 特有 API | TECH 2.1 |
| MKC-TC-S1-2-027 | Compatibility | Integration | P1 | Web 端登录后跳转首页 | ChromeDriver | 执行集成测试 | Splash → 登录 → 首页导航成功 | PRD Web AC |

## 4. 测试执行清单

- [ ] 登录/注册表单校验分支
- [ ] 登录成功跳转与 token 持久化
- [ ] 登录失败错误提示
- [ ] 注册成功与重复邮箱错误
- [ ] Splash 自动检查 token 并跳转
- [ ] 路由重定向保护首页
- [ ] `AuthNotifier` 状态变化单元测试
- [ ] `flutter test` 全部通过（含 `flutter test --platform chrome` 至少运行一次）
- [ ] `flutter analyze` 0 issues
- [ ] 集成测试覆盖登录 → 首页流程（Android/iOS/Web 任选其一）

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
