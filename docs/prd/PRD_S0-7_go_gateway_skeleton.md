# PRD：[S0-7] 搭建 Go Gateway 项目骨架

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](../AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-7 |
| **任务名称** | 搭建 Go Gateway 项目骨架 |
| **所属史诗** | E0 基础设施 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S0-1 仓库初始化 |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要在 `gateway/` 目录下搭建一个基于 Gin 框架的 Go 网关服务项目骨架，包含标准分层目录、配置加载、数据库连接、Redis 连接、健康检查接口和统一的错误响应中间件。该骨架将作为所有业务 API 的入口。

---

## 验收标准（AC）

- [ ] 使用 `go mod init github.com/coderZsq/mkc/gateway` 初始化模块
- [ ] 项目目录按 `cmd/`、`internal/`、`pkg/`、`config/` 分层
- [ ] 集成 Gin Web 框架
- [ ] 集成 GORM + MySQL 驱动
- [ ] 集成 go-redis/v9
- [ ] 实现配置文件加载（Viper 或 envconfig），支持 dev/prod 环境
- [ ] 实现 `/health` 健康检查接口，返回服务状态和依赖状态
- [ ] 实现统一错误响应中间件和请求日志中间件
- [ ] `go build ./cmd/server` 成功编译
- [ ] `go test ./...` 通过（至少包含 health handler 测试）
- [ ] 编写 Dockerfile 和 K8s deployment 初稿
- [ ] README 说明启动命令、配置项和目录结构

---

## 推荐目录结构

```
gateway/
├── cmd/
│   └── server/
│       └── main.go               # 程序入口
├── internal/
│   ├── config/
│   │   └── config.go             # 配置结构体与加载
│   ├── handler/
│   │   └── health_handler.go     # 健康检查 handler
│   ├── middleware/
│   │   ├── error_handler.go      # 统一错误响应
│   │   ├── logger.go             # 请求日志
│   │   └── recovery.go           # panic 恢复
│   ├── model/
│   │   └── base.go               # 基础模型
│   ├── repository/
│   │   └── base.go               # 通用仓储
│   ├── router/
│   │   └── router.go             # 路由注册
│   └── service/
│       └── health_service.go     # 健康检查业务
├── pkg/
│   ├── response/
│   │   └── response.go           # 统一响应封装
│   └── errors/
│       └── errors.go             # 业务错误码
├── config/
│   ├── config.yaml               # 配置文件示例
│   └── config.example.yaml
├── Dockerfile
├── go.mod
├── go.sum
├── Makefile
└── README.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| gin-gonic/gin | v1.10+ | Web 框架 |
| gorm.io/gorm | v1.25+ | ORM |
| gorm.io/driver/mysql | v1.5+ | MySQL 驱动 |
| redis/go-redis/v9 | v9.x | Redis 客户端 |
| spf13/viper | v1.19+ | 配置管理 |
| golang-jwt/jwt/v5 | v5.x | JWT 生成与校验 |
| stretchr/testify | v1.9+ | 单元测试 |
| swaggo/gin-swagger | latest | Swagger 文档 |

---

## 技术要点

### 配置管理

```yaml
server:
  port: 8080
  mode: debug          # debug / release

database:
  host: mysql
  port: 3306
  user: mkc
  password: ""
  dbname: mkc
  max_open: 25
  max_idle: 5

redis:
  addr: redis:6379
  password: ""
  db: 0

jwt:
  secret: "change-me"
  access_ttl: 15m
```

### 健康检查接口

```json
GET /health
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "v0.1.0",
    "checks": {
      "mysql": "ok",
      "redis": "ok"
    }
  }
}
```

### 统一响应封装

```go
package response

func OK(c *gin.Context, data any) {
    c.JSON(http.StatusOK, gin.H{
        "success": true,
        "data": data,
        "error": nil,
        "meta": nil,
    })
}

func Fail(c *gin.Context, code int, errCode, message string) {
    c.JSON(code, gin.H{
        "success": false,
        "data": nil,
        "error": gin.H{
            "code": errCode,
            "message": message,
        },
        "meta": nil,
    })
}
```

---

## 文件位置

```
gateway/
├── cmd/server/main.go
├── internal/
│   ├── config/
│   ├── handler/
│   ├── middleware/
│   ├── model/
│   ├── repository/
│   ├── router/
│   └── service/
├── pkg/
├── config/
├── Dockerfile
├── go.mod
├── Makefile
└── README.md
```

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 依赖版本不兼容 | build 失败 | 使用 go modules 版本锁定，及时 `go mod tidy` |
| 配置加载方式选择困难 | 开发效率低 | Sprint 0 用 Viper + YAML，后续可切换为环境变量优先 |
| 目录分层过度设计 | 开发阻力大 | 保持核心分层，后续按需扩展 |

---

## 备注

- 本任务只搭建骨架，不实现业务接口
- Dockerfile 采用多阶段构建，减小镜像体积
- 健康检查接口是 Sprint 0 Demo 的关键展示点
- 后续 Sprint 会补充认证、上传、任务、SSE 等 handler
