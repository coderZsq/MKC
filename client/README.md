# MKC Client

Flutter 跨端客户端，基于 Clean Architecture + Riverpod。

## 目录结构

```
lib/
├── main.dart
├── app.dart
├── config/
├── data/
│   ├── datasources/
│   ├── models/
│   └── repositories/
├── domain/
│   ├── entities/
│   ├── repositories/
│   └── usecases/
├── presentation/
│   ├── pages/
│   ├── widgets/
│   ├── providers/
│   └── state/
└── shared/
    ├── constants/
    ├── errors/
    ├── extensions/
    └── utils/
```

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
