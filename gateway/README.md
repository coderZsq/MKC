# MKC Gateway

Go 网关服务，基于 [Gin](https://github.com/gin-gonic/gin) + [GORM](https://gorm.io) + [Redis](https://github.com/redis/go-redis) + JWT，为多媒体知识助手提供统一入口。

## 目录结构

```
gateway/
├── cmd/
│   ├── migrate/            # 数据库迁移入口（独立命令）
│   └── server/             # HTTP 服务入口
├── internal/               # 私有代码，禁止外部引用
│   ├── config/             # 配置加载与校验
│   ├── handler/            # HTTP handler
│   ├── middleware/         # Gin 中间件
│   ├── model/              # GORM 数据模型
│   ├── repository/         # 数据库 / Redis 连接与迁移
│   ├── router/             # 路由注册
│   └── service/            # 业务逻辑
├── pkg/                    # 可复用公共包
│   ├── errors/             # 业务错误码
│   ├── jwt/                # JWT 签发与解析
│   ├── logger/             # Zap 日志封装
│   ├── password/           # bcrypt 密码工具
│   └── response/           # 统一响应信封
├── config/
│   └── config.example.yaml # 配置示例（无真实密钥）
├── migrations/             # SQL migration 文件
├── k8s/                    # Kubernetes 部署初稿
├── Dockerfile
├── Makefile
└── README.md
```

## 环境要求

- Go 1.22+
- MySQL 8.0（可选，缺失时服务降级启动）
- Redis 6+（可选，缺失时服务降级启动）

## 快速启动

```bash
cd gateway
cp config/config.example.yaml config/config.yaml
# 按需修改 config/config.yaml
make run
```

服务默认监听 `8080`，访问：

```bash
curl http://localhost:8080/health
```

## 配置说明

配置通过 Viper 从 YAML 加载，并支持 `APP_` 前缀的环境变量覆盖，例如：

```bash
APP_SERVER_PORT=9090 APP_LOG_LEVEL=debug make run
```

关键配置项：

| 路径 | 说明 | 示例 |
|---|---|---|
| `app.name` | 服务名称 | `mkc-gateway` |
| `app.version` | 版本号 | `0.1.0` |
| `app.env` | 运行环境 | `dev` / `prod` |
| `server.port` | HTTP 端口 | `8080` |
| `server.mode` | Gin 模式 | `debug` / `release` |
| `log.level` | 日志级别 | `info` / `debug` |
| `log.format` | 日志格式 | `json` / `console` |
| `mysql.*` | MySQL 连接池配置 | 见示例文件 |
| `redis.*` | Redis 连接配置 | 见示例文件 |
| `jwt.secret` | JWT 签名密钥 | 通过环境变量覆盖 |
| `ai_service.base_url` | 内部 AI 服务地址 | `http://ai-service:5000` |

## 常用命令

```bash
# 运行测试
make test

# 构建二进制
make build

# 代码静态检查（需安装 golangci-lint）
make lint

# 数据库迁移
make migrate-up
make migrate-down

# 构建 Docker 镜像
make docker
```

## 健康检查

`GET /health` 与 `GET /api/v1/health` 返回统一响应信封：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "checks": {
      "mysql": "ok",
      "redis": "ok"
    }
  },
  "error": null,
  "meta": null
}
```

当 MySQL 或 Redis 不可用时，状态为 `degraded`，对应检查项为 `down`，服务仍可启动。

## Docker

```bash
docker build -t mkc-gateway:latest .
docker run -p 8080:8080 mkc-gateway:latest
```

镜像使用多阶段构建，运行时以非 root 用户运行。

## Kubernetes

`k8s/` 目录提供最小可运行的部署草稿，需根据实际环境补充镜像仓库、ConfigMap、Secret 等：

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Swagger

启动服务后访问：

```bash
curl http://localhost:8080/swagger/index.html
```

> 当前 Sprint 0 仅包含基础骨架与 `/health` 接口，业务 API 将在后续 Sprint 补充。
