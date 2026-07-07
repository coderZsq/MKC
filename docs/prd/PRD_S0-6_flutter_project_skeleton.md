# PRD：[S0-6] 搭建 Flutter 项目骨架

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](../AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-6 |
| **任务名称** | 搭建 Flutter 项目骨架 |
| **所属史诗** | E0 基础设施 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S0-1 仓库初始化 |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要在 `client/` 目录下初始化一个生产级的 Flutter 项目，采用 Clean Architecture 分层，集成 Riverpod 状态管理、路由、网络库和基础主题。该骨架为后续登录页、上传页、任务中心、对话页的开发提供统一结构。

---

## 验收标准（AC）

- [ ] `flutter create client --org com.example.mkc` 初始化项目
- [ ] 目录结构按 Clean Architecture 划分为 `data/`、`domain/`、`presentation/`
- [ ] 集成 Riverpod 状态管理（flutter_riverpod）
- [ ] 集成 go_router 路由
- [ ] 集成 dio 网络库并封装基础 HTTP client
- [ ] 配置环境管理（dev / prod）和基础主题
- [ ] 提供启动页（Splash Page）和空首页占位
- [ ] `flutter analyze` 无错误
- [ ] `flutter test` 可运行（至少一个示例测试通过）
- [ ] README 说明项目结构、启动命令和依赖版本

---

## 推荐目录结构

```
client/
├── android/
├── ios/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   ├── config/
│   │   ├── env.dart              # 环境配置
│   │   ├── theme.dart            # 主题配置
│   │   └── constants.dart        # 常量
│   ├── data/
│   │   ├── datasources/
│   │   │   └── remote/           # API 数据源
│   │   ├── models/
│   │   ├── repositories/
│   │   └── mappers/
│   ├── domain/
│   │   ├── entities/
│   │   ├── repositories/         # 抽象仓库接口
│   │   └── usecases/
│   ├── presentation/
│   │   ├── pages/
│   │   ├── widgets/
│   │   ├── providers/
│   │   └── viewmodels/
│   └── shared/
│       ├── errors/
│       ├── result.dart           # Result<T, E> 类型
│       └── extensions/
├── test/
│   └── widget_test.dart
├── pubspec.yaml
└── README.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| flutter_riverpod | ^2.5.x | 状态管理 |
| go_router | ^14.x | 路由 |
| dio | ^5.x | HTTP 客户端 |
| freezed_annotation | ^2.x | 不可变数据类 |
| json_annotation | ^4.x | JSON 序列化 |
| flutter_secure_storage | ^9.x | Token 安全存储 |
| logger | ^2.x | 日志 |

**dev_dependencies**：
- build_runner
- freezed
- json_serializable
- mockito
- flutter_lints

---

## 技术要点

### Clean Architecture 分层

- **data**：实现仓库接口，包含远程/本地数据源、模型、mapper
- **domain**：业务实体、仓库接口、用例，不依赖 Flutter 框架
- **presentation**：页面、组件、状态机（Riverpod StateNotifier）

### 状态管理约定

- 使用 `StateNotifier` + `AsyncValue` 封装页面状态机
- 状态分类：`initial`、`loading`、`success`、`failure`、`empty`
- Provider 按功能模块组织：`auth_provider.dart`、`upload_provider.dart`

### 网络层约定

- 封装 `ApiClient`，统一处理 baseUrl、超时、Token 注入、错误转换
- 后端返回统一响应信封，ApiClient 负责解包
- Token 刷新逻辑在拦截器中实现

### 路由约定

```dart
const String splashRoute = '/';
const String loginRoute = '/login';
const String homeRoute = '/home';
```

---

## 文件位置

```
client/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   ├── config/
│   ├── data/
│   ├── domain/
│   ├── presentation/
│   └── shared/
├── test/
├── pubspec.yaml
└── README.md
```

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 目录结构过于复杂导致初期开发阻力大 | 拖慢 Sprint 1 | 先保证三层划分，细节随需求补充 |
| 依赖版本冲突 | build_runner 失败 | 使用稳定版本组合，定期 `flutter pub upgrade` |
| Flutter Web 支持不完整 | 后续部署 Demo 受限 | MVP 阶段优先 iOS/Android，Web 在 Sprint 5 适配 |

---

## 备注

- 本任务只搭建骨架，不实现具体业务页面
- 示例测试可以先写一个 Counter 或 Splash 页面测试占位
- 后续 Sprint 逐步添加 login、upload、tasks、chat 等页面
