# S0-7 测试用例：Go Gateway 服务骨架

## 1. 范围与目标

验证 `gateway/` 目录下 Go 服务已按分层架构初始化，包含 `cmd/`、`internal/`、`pkg/`、`config/`、`migrations/`，集成 Gin、GORM、Redis、JWT、日志、配置加载、Swagger 与可运行的单元/集成测试。

## 2. 测试环境

- Go 1.22+ 已安装
- 本地 MySQL 8.0 容器或 K8s MySQL 可选
- 本地 Redis 容器可选
- 已执行 `cd gateway && go mod download`

## 3. 测试用例

### 3.1 目录结构与文件存在性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-001 | Functional | Static | P0 | `gateway/go.mod` 存在 | 仓库已克隆 | `ls gateway/go.mod` | 文件存在 | PRD AC-1 |
| MKC-TC-S0-7-002 | Functional | Static | P0 | `gateway/cmd/server/main.go` 存在 | 仓库已克隆 | `ls gateway/cmd/server/main.go` | 文件存在 | PRD AC-2 |
| MKC-TC-S0-7-003 | Functional | Static | P0 | 分层目录 `internal/` 存在 | 仓库已克隆 | `ls -d gateway/internal/config gateway/internal/handler gateway/internal/service gateway/internal/repository gateway/internal/model gateway/internal/middleware gateway/internal/pkg 2>/dev/null` | 关键分层目录均存在 | PRD AC-2 |
| MKC-TC-S0-7-004 | Functional | Static | P1 | `gateway/pkg/` 存在通用工具 | 仓库已克隆 | `ls gateway/pkg/` | 存在 logger、response、errors 等子目录 | PRD 推荐目录结构 |
| MKC-TC-S0-7-005 | Functional | Static | P1 | `gateway/config/` 包含配置文件 | 仓库已克隆 | `ls gateway/config/` | 存在 config.yaml / config.yaml.example | PRD 推荐目录结构 |
| MKC-TC-S0-7-006 | Functional | Static | P1 | `gateway/migrations/` 目录存在 | 仓库已克隆 | `ls gateway/migrations/` | 目录存在且至少有一对 up/down migration 文件 | PRD AC-8 |
| MKC-TC-S0-7-007 | Functional | Static | P1 | `gateway/Makefile` 存在 | 仓库已克隆 | `ls gateway/Makefile` | 文件存在 | PRD AC-9 |
| MKC-TC-S0-7-008 | Boundary | Static | P2 | 文件大小符合小文件原则 | 仓库已克隆 | `find gateway -type f -name "*.go" -exec wc -l {} + | sort -n | tail -10` | 单文件不超过 800 行 | 代码规范 |

### 3.2 Go 版本与依赖

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-009 | Functional | Static | P0 | Go 版本 >= 1.22 | 文件存在 | `head -n 5 gateway/go.mod` | `go 1.22` 或更高 | PRD 技术要点 |
| MKC-TC-S0-7-010 | Functional | Static | P0 | 声明 `github.com/gin-gonic/gin` | 文件存在 | `grep "gin-gonic/gin" gateway/go.mod` | 版本形如 `v1.9.x` | PRD 核心依赖 |
| MKC-TC-S0-7-011 | Functional | Static | P0 | 声明 `gorm.io/gorm` 与 `gorm.io/driver/mysql` | 文件存在 | `grep -E "gorm.io/gorm|gorm.io/driver/mysql" gateway/go.mod` | 均存在 | PRD 核心依赖 |
| MKC-TC-S0-7-012 | Functional | Static | P0 | 声明 `github.com/redis/go-redis/v9` | 文件存在 | `grep "redis/go-redis/v9" gateway/go.mod` | 版本形如 `v9.x` | PRD 核心依赖 |
| MKC-TC-S0-7-013 | Functional | Static | P1 | 声明 `github.com/spf13/viper` | 文件存在 | `grep "spf13/viper" gateway/go.mod` | 版本形如 `v1.19.x` | PRD 核心依赖 |
| MKC-TC-S0-7-014 | Functional | Static | P1 | 声明 `github.com/golang-jwt/jwt/v5` | 文件存在 | `grep "golang-jwt/jwt/v5" gateway/go.mod` | 版本形如 `v5.x` | PRD 核心依赖 |
| MKC-TC-S0-7-015 | Functional | Static | P1 | 声明 `golang.org/x/crypto/bcrypt` | 文件存在 | `grep "golang.org/x/crypto" gateway/go.mod` | 存在 | PRD 核心依赖 |
| MKC-TC-S0-7-016 | Functional | Static | P1 | 声明日志库 `go.uber.org/zap` | 文件存在 | `grep "go.uber.org/zap" gateway/go.mod` | 版本形如 `v1.27.x` | PRD 核心依赖 |
| MKC-TC-S0-7-017 | Functional | Static | P1 | 声明 Swagger 库 `github.com/swaggo/gin-swagger` | 文件存在 | `grep "swaggo/gin-swagger" gateway/go.mod` | 存在 | PRD 核心依赖 |
| MKC-TC-S0-7-018 | Functional | Static | P1 | 声明测试库 `github.com/stretchr/testify` | 文件存在 | `grep "stretchr/testify" gateway/go.mod` | 存在 | PRD 核心依赖 |

### 3.3 编译与运行

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-019 | Functional | Integration | P0 | `go mod download` 成功 | 进入 gateway 目录 | `go mod download` | 无错误 | PRD AC-1 |
| MKC-TC-S0-7-020 | Functional | Integration | P0 | `go build ./cmd/server` 成功 | 依赖已下载 | `go build -o bin/server ./cmd/server` | 生成可执行文件，无编译错误 | PRD AC-3 |
| MKC-TC-S0-7-021 | Functional | Integration | P0 | 无依赖冲突或安全漏洞（基础检查） | 依赖已下载 | `go mod tidy && go mod verify` | 成功 | 工程最佳实践 |
| MKC-TC-S0-7-022 | Functional | Integration | P1 | `go vet ./...` 无错误 | 代码存在 | `go vet ./...` | 无 error | PRD 代码质量 |
| MKC-TC-S0-7-023 | Functional | Integration | P1 | `golangci-lint run` 通过 | 已安装 golangci-lint | `golangci-lint run ./...` | 无 error | PRD 工作流设计 |
| MKC-TC-S0-7-024 | Functional | Integration | P0 | `go test ./...` 通过 | 代码存在 | `go test ./...` | 至少基础测试通过 | PRD AC-7 |
| MKC-TC-S0-7-025 | Functional | Integration | P1 | 健康检查接口可访问 | 服务已启动 | `curl http://localhost:8080/health` | 返回 JSON，status 为 ok/up | PRD AC-5 |
| MKC-TC-S0-7-026 | Functional | Integration | P1 | Swagger UI 可访问 | 服务已启动 | `curl -I http://localhost:8080/swagger/index.html` | 返回 200 | PRD 技术要点 |

### 3.4 配置加载

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-027 | Functional | Static | P0 | 配置文件示例存在且不包含真实密码 | 文件存在 | `cat gateway/config/config.yaml.example` | 密码字段为占位符 | 安全基线 |
| MKC-TC-S0-7-028 | Functional | Unit | P1 | Viper 可加载 YAML 配置 | 代码存在 | 运行 config 包测试 | 正确解析 server.port、database.dsn、redis.addr 等 | PRD 核心依赖 |
| MKC-TC-S0-7-029 | Functional | Unit | P1 | 环境变量覆盖配置生效 | 代码存在 | 设置 `APP_SERVER_PORT=9090` 后测试 | 配置中端口为 9090 | PRD 技术要点 |
| MKC-TC-S0-7-030 | Negative | Unit | P1 | 缺少必填配置时启动失败 | 代码存在 | 删除 `database.dsn` 后测试 | 返回明确错误，不 panic | PRD 错误处理 |

### 3.5 数据库与 Redis 集成

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-031 | Functional | Integration | P0 | GORM 可连接 MySQL | MySQL 已运行 | 启动服务或运行集成测试 | 连接成功，AutoMigrate 无错误 | PRD AC-4 |
| MKC-TC-S0-7-032 | Functional | Integration | P0 | go-redis 可连接 Redis | Redis 已运行 | 启动服务或运行集成测试 | 连接成功，可 ping 通 | PRD AC-4 |
| MKC-TC-S0-7-033 | Functional | Integration | P1 | 数据库连接池参数可配置 | 配置存在 | 查看 config.yaml.example | 包含 max_open_conns、max_idle_conns、conn_max_lifetime | PRD 技术要点 |
| MKC-TC-S0-7-034 | Functional | Integration | P1 | Redis 连接失败时服务给出明确日志 | Redis 未启动 | 启动服务 | 日志提示 Redis 连接失败，服务可优雅降级或退出 | PRD 错误处理 |
| MKC-TC-S0-7-035 | Functional | Integration | P1 | 数据库连接失败时服务给出明确日志 | MySQL 未启动 | 启动服务 | 日志提示数据库连接失败 | PRD 错误处理 |

### 3.6 HTTP 路由与中间件

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-036 | Functional | Static | P0 | Gin 路由注册入口存在 | 文件存在 | 阅读 `gateway/cmd/server/main.go` 或 `internal/handler/router.go` | 存在 `gin.Default()` 与路由注册 | PRD AC-2 |
| MKC-TC-S0-7-037 | Functional | Unit | P1 | 健康检查 handler 返回统一响应信封 | 代码存在 | 运行 handler 测试 | 响应 JSON 为 `{success, data, error, meta}` | PRD API 设计 |
| MKC-TC-S0-7-038 | Functional | Static | P1 | 存在 Recovery / Logger 中间件 | 文件存在 | 阅读 `internal/middleware/` | 存在 recovery 与 request logger 中间件 | PRD 中间件约定 |
| MKC-TC-S0-7-039 | Functional | Unit | P2 | 未匹配路由返回 404 且信封统一 | 代码存在 | 测试 `/not-exist` | 返回 404 + `{success:false, error:{code,message}}` | PRD API 设计 |
| MKC-TC-S0-7-040 | Functional | Unit | P2 | Panic 被 Recovery 捕获并返回 500 信封 | 代码存在 | 触发 handler panic | 返回 500，不泄露堆栈，日志记录 panic | PRD 中间件约定 |

### 3.7 日志与可观测性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-041 | Functional | Static | P1 | zap logger 封装存在 | 文件存在 | `ls gateway/pkg/logger/` 或 `internal/pkg/logger/` | 存在 logger.go | PRD 推荐目录结构 |
| MKC-TC-S0-7-042 | Functional | Integration | P1 | 日志输出为 JSON 且包含 trace_id/request_id | 服务运行 | 发起请求并查看日志 | 日志为 JSON，包含 level、time、msg、trace_id 等字段 | PRD 可观测性 |
| MKC-TC-S0-7-043 | Functional | Integration | P2 | 日志级别可通过配置切换 | 配置文件存在 | 修改 `log.level` 为 debug | 输出 debug 级别日志 | PRD 技术要点 |

### 3.8 统一响应与错误处理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-044 | Functional | Static | P0 | `pkg/response` 统一响应封装存在 | 文件存在 | `ls gateway/pkg/response/` | 存在 response.go | PRD API 设计 |
| MKC-TC-S0-7-045 | Functional | Unit | P1 | `response.Success` 返回正确信封 | 代码存在 | 运行 response 测试 | 返回 `{success:true, data:..., error:null, meta:null}` | PRD API 设计 |
| MKC-TC-S0-7-046 | Functional | Unit | P1 | `response.Error` 返回正确错误信封 | 代码存在 | 运行 response 测试 | 返回 `{success:false, data:null, error:{code,message}, meta:null}` | PRD API 设计 |
| MKC-TC-S0-7-047 | Functional | Unit | P1 | 业务错误码常量已定义 | 文件存在 | `grep -R "BAD_REQUEST\|UNAUTHORIZED\|NOT_FOUND" gateway/internal/pkg/errors/` | 存在错误码常量 | PRD 错误码规范 |

### 3.9 测试与质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-048 | Functional | Unit | P1 | handler 层单元测试存在 | 文件存在 | `find gateway/internal/handler -name "*_test.go"` | 至少存在一个测试文件 | PRD AC-7 |
| MKC-TC-S0-7-049 | Functional | Unit | P1 | service 层单元测试存在 | 文件存在 | `find gateway/internal/service -name "*_test.go"` | 至少存在一个测试文件 | PRD AC-7 |
| MKC-TC-S0-7-050 | Functional | Unit | P1 | repository 层单元测试存在 | 文件存在 | `find gateway/internal/repository -name "*_test.go"` | 至少存在一个测试文件 | PRD AC-7 |
| MKC-TC-S0-7-051 | Functional | Integration | P1 | 集成测试使用 testify + MySQL/Redis 容器 | 代码存在 | 运行 `go test ./... -tags=integration` | 有集成测试标签或独立的 integration 测试文件 | PRD 测试策略 |
| MKC-TC-S0-7-052 | Performance | Integration | P2 | 健康接口 100 次并发请求稳定 | 服务运行 | `ab -n 1000 -c 100 http://localhost:8080/health` 或等效脚本 | 全部返回 200，无 panic | PRD 工作流设计 |

### 3.10 Docker 与部署

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-053 | Functional | Static | P1 | `gateway/Dockerfile` 存在 | 仓库已克隆 | `ls gateway/Dockerfile` | 文件存在 | PRD 部署文件 |
| MKC-TC-S0-7-054 | Functional | Integration | P1 | Docker 镜像构建成功 | Docker 可用 | `docker build -t mkc-gateway:latest gateway/` | 构建成功 | PRD AC-6 |
| MKC-TC-S0-7-055 | Functional | Integration | P2 | 容器启动后健康检查通过 | 镜像已构建 | `docker run -p 8080:8080 mkc-gateway:latest` | `/health` 返回 200 | PRD AC-6 |
| MKC-TC-S0-7-056 | Security | Static | P2 | Dockerfile 使用非 root 用户 | 文件存在 | `grep -E "USER|RUN adduser" gateway/Dockerfile` | 使用非 root 运行 | 安全基线 |

### 3.11 Makefile 与脚本

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-057 | Functional | Static | P1 | Makefile 包含 run/test/build/lint 目标 | 文件存在 | `cat gateway/Makefile` | 包含 `run`、`test`、`build`、`lint` | PRD AC-9 |
| MKC-TC-S0-7-058 | Functional | Integration | P1 | `make test` 成功 | 依赖已安装 | `cd gateway && make test` | 运行 `go test ./...` 并通过 | PRD AC-9 |
| MKC-TC-S0-7-059 | Functional | Integration | P1 | `make build` 生成二进制 | 依赖已安装 | `cd gateway && make build` | 生成 `bin/server` 或等效文件 | PRD AC-9 |
| MKC-TC-S0-7-060 | Functional | Integration | P2 | `make lint` 通过 | 已安装 golangci-lint | `cd gateway && make lint` | 运行 lint 无错误 | PRD AC-9 |

### 3.12 安全与边界

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-7-061 | Security | Static | P0 | 代码中无硬编码密码或密钥 | 代码存在 | `grep -R "password\|secret\|token" gateway/ --include="*.go"` | 仅出现占位符或环境变量名 | 安全基线 |
| MKC-TC-S0-7-062 | Security | Static | P1 | JWT secret 从环境变量读取 | 代码存在 | 阅读 `internal/config/` 或 `internal/pkg/jwt/` | 不硬编码 secret | PRD 认证方式 |
| MKC-TC-S0-7-063 | Boundary | Integration | P2 | 服务启动时若端口被占用给出明确错误 | 8080 已被占用 | 启动服务 | 日志提示 `bind: address already in use` 并退出 | PRD 错误处理 |
| MKC-TC-S0-7-064 | Concurrency | Integration | P2 | 多 goroutine 同时访问 Redis/MySQL 无竞态 | 测试存在 | `go test ./... -race` | 无 data race 报告 | PRD 工作流设计 |
| MKC-TC-S0-7-065 | Idempotency | Integration | P2 | 重复 `go test ./...` 结果一致 | 测试已通过 | 连续运行 3 次 | 结果一致 | 工程最佳实践 |

## 4. 测试执行清单

- [ ] `gateway/go.mod` Go 版本 >= 1.22
- [ ] 核心依赖（Gin/GORM/Redis/Viper/JWT/bcrypt/zap/Swagger/testify）均已声明
- [ ] `go build ./cmd/server` 成功
- [ ] `go test ./...` 通过
- [ ] `golangci-lint run ./...` 通过
- [ ] `/health` 接口返回统一响应信封
- [ ] Viper 配置加载与环境变量覆盖正确
- [ ] MySQL/Redis 连接正常
- [ ] Dockerfile 构建成功
- [ ] Makefile 常用目标可用
- [ ] 无硬编码密钥/密码

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
