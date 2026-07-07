# MKC Client

Flutter 跨端客户端，基于 Clean Architecture + Riverpod。

## 目录结构

```
lib/
├── main.dart
├── app.dart                     # 应用根节点（Riverpod + go_router）
├── config/
│   ├── env.dart                 # 环境配置（dev / prod）
│   ├── theme.dart               # 主题配置
│   └── constants.dart           # 常量
├── data/
│   ├── datasources/
│   │   ├── remote/              # Dio / ApiClient
│   │   └── secure/              # flutter_secure_storage 封装
│   ├── models/                  # DTO
│   ├── repositories/            # 仓库实现
│   └── mappers/                 # 模型映射
├── domain/
│   ├── entities/                # 业务实体
│   ├── repositories/            # 仓库接口
│   └── usecases/                # 用例
├── presentation/
│   ├── pages/                   # 页面
│   ├── widgets/                 # 可复用组件
│   ├── providers/               # Riverpod Provider / Notifier
│   └── state/                   # 状态类
└── shared/
    ├── constants/
    ├── errors/                  # AppException 层级
    ├── result.dart              # Result<T> 类型
    ├── extensions/
    └── utils/
```

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| flutter_riverpod | ^2.5.1 | 状态管理 |
| go_router | ^14.1.4 | 路由 |
| dio | ^5.4.3 | HTTP 客户端 |
| freezed_annotation | ^2.4.1 | 不可变数据类 |
| json_annotation | ^4.9.0 | JSON 序列化 |
| flutter_secure_storage | ^9.2.2 | Token 安全存储 |
| logger | ^2.4.0 | 日志 |

## 启动

```bash
cd client
flutter pub get
flutter run
```

## 测试

```bash
flutter analyze
flutter test
```

## 环境切换

开发环境（默认）：

```bash
flutter run
```

生产环境：

```bash
flutter run --dart-define=APP_ENV=prod --dart-define=BASE_URL=https://mkc.prod/api/v1
```
