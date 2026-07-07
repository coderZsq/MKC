# MKC Gateway

Go 网关服务，基于 Gin + GORM + Redis + JWT。

## 目录结构

```
gateway/
├── cmd/server/       # 程序入口
├── internal/         # 私有代码
│   ├── config/
│   ├── handler/
│   ├── middleware/
│   ├── model/
│   ├── repository/
│   ├── router/
│   └── service/
├── pkg/              # 可复用包
├── migrations/       # 数据库迁移
└── config/           # 配置文件
```

## 启动

```bash
cd gateway
cp config/config.example.yaml config/config.yaml
# 修改配置后
make run
```

## 测试

```bash
make test
```

## Docker

```bash
make docker
```
