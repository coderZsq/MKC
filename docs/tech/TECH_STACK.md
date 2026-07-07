# MKC 技术选型总览

> 项目：MKC — Multimedia Knowledge Companion  
> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 级别：架构师总览

---

## 1. 项目定位

MKC 是一个面向个人知识管理的多媒体 AI 伴侣，核心能力包括：

- MP3 音频转录为 SRT/文本
- PDF 文档解析与结构化抽取
- 基于 Embedding + 向量检索的 RAG 知识库问答
- 多轮对话与引用溯源

技术栈覆盖：Flutter 跨端客户端、Go 云原生网关、Python AI 服务、Kubernetes 本地/生产部署。

---

## 2. 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          客户端层                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Flutter (iOS / Android / Web / Desktop)     │   │
│  │  Riverpod + go_router + dio + flutter_secure_storage     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                          网关层                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Go Gateway (Gin + GORM + JWT)               │   │
│  │  Auth · Resource · Task · Conversation · SSE Proxy       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│     MySQL       │ │     Redis       │ │      MinIO          │
│  业务元数据      │ │  Session/缓存    │ │   对象存储          │
└─────────────────┘ └─────────────────┘ └─────────────────────┘
                              │
                              ▼ 内部调用
┌─────────────────────────────────────────────────────────────────┐
│                         AI 服务层                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Python AI Service (Flask + Celery)             │   │
│  │  ASR · PDF Parser · Embedding · RAG · LLM                │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌───────────────────────┐   ┌───────────────────────┐
│        Milvus         │   │  OpenAI / 智谱 / Ollama │
│     向量数据库         │   │      大语言模型          │
└───────────────────────┘   └───────────────────────┘
```

---

## 3. 技术选型矩阵

### 3.1 前端技术栈

| 领域 | 选型 | 版本 | 选型理由 |
|---|---|---|---|
| 跨端框架 | Flutter | 3.22+ | 一套代码覆盖 iOS/Android/Web/Desktop，符合 AI 应用工程师技能栈 |
| 状态管理 | flutter_riverpod | 2.5+ | 编译安全、依赖注入、测试友好，替代 Provider |
| 状态类 | StateNotifier + freezed | - | 不可变状态，类型安全 |
| 路由 | go_router | 14.1+ | 声明式路由，与 Riverpod 配合良好 |
| 网络请求 | dio | 5.4+ | 拦截器、Token 刷新、SSE 支持 |
| Token 存储 | flutter_secure_storage | 9.2+ | refresh_token 安全存储 |
| 偏好存储 | shared_preferences | 2.2+ | 轻量配置缓存 |
| JSON/模型 | freezed + json_serializable | 2.5+ / 6.8+ | 自动生成不可变模型 |
| UI 适配 | flutter_screenutil | 5.9+ | 屏幕适配 |
| 文件选择 | file_picker | 8.0+ | 上传入口 |
| 国际化 | intl | 0.19+ | 多语言预留 |

### 3.2 Gateway 后端技术栈（Go）

| 领域 | 选型 | 版本 | 选型理由 |
|---|---|---|---|
| Web 框架 | Gin | 1.10+ | 高性能、中间件丰富、社区主流 |
| ORM | GORM | 1.25+ | 开发效率高，AutoMigrate 适合 Sprint 0 快速迭代 |
| MySQL 驱动 | gorm.io/driver/mysql | - | 原生 MySQL 支持 |
| Redis 客户端 | go-redis/v9 | 9.5+ | 官方维护，Cluster/Sentinel 支持好 |
| 配置管理 | Viper | 1.19+ | YAML + 环境变量 + 热加载 |
| JWT | golang-jwt/jwt/v5 | 5.x | 社区标准，支持 v5 Claims |
| 密码哈希 | bcrypt | 标准库 | 安全、成熟 |
| 日志 | zap | 1.27+ | 高性能结构化日志 |
| API 文档 | swaggo | 1.16+ | 从注释生成 Swagger |
| 可观测 | OpenTelemetry-Go | 1.27+ | 统一 Trace/Metrics |
| 测试 | testify | 1.9+ | 断言 + Mock |

### 3.3 AI 服务技术栈（Python）

| 领域 | 选型 | 版本 | 选型理由 |
|---|---|---|---|
| Web 框架 | Flask | 3.0.x | 轻量、灵活、SSE 友好 |
| 任务队列 | Celery | 5.4+ | 异步任务、分布式、重试机制 |
| Broker/Backend | Redis | 5.x | 与 Celery 配合成熟 |
| WSGI | gunicorn + gevent | 22.x | 生产部署、长连接支持 |
| 配置 | pydantic-settings | 2.x | 类型安全、环境变量映射 |
| 测试 | pytest + pytest-cov | 8.x | 覆盖率驱动 |
| 代码质量 | black + ruff + mypy | 24.x / 0.5+ / 1.10+ | 格式化 + 静态检查 + 类型检查 |
| ASR | faster-whisper | - | 本地/边缘 ASR，支持多语言 |
| PDF 解析 | pymupdf + pdfplumber | - | 文本/布局/表格综合解析 |
| Embedding | BGE-M3 / text-embedding-v3 | - | 多语言、长文本、效果好 |
| 向量数据库 | Milvus | 2.4+ | 高性能向量检索、K8s 原生 |
| RAG 编排 | LangGraph + LlamaIndex | - | 复杂多跳推理 + 索引构建 |
| LLM | OpenAI API / 智谱 / Ollama | - | 可插拔模型后端 |

### 3.4 数据与中间件

| 用途 | 选型 | 版本 | 说明 |
|---|---|---|---|
| 业务数据库 | MySQL | 8.0.37+ | utf8mb4，用户/资源/任务/会话/消息 |
| 缓存/Session | Redis | 7.2+ | refresh_token、限流、Celery broker |
| 对象存储 | MinIO | RELEASE.2024-05+ | 文件上传/下载/SRT 输出 |
| 向量数据库 | Milvus | 2.4+ | Embedding 存储与相似度检索 |

### 3.5 基础设施

| 领域 | 选型 | 说明 |
|---|---|---|
| 本地集群 | Docker Desktop Kubernetes | 与 Docker 共用 Daemon，开发链路短 |
| 生产集群 | 云厂商托管 K8s（EKS/ACK/GKE） | 按需选择 |
| Ingress | nginx-ingress-controller | 流量入口、TLS 终止 |
| 证书 | cert-manager | 自动 TLS（生产） |
| Secret 管理 | K8s Secret（本地）/ External Secrets Operator（生产） | 渐进式 |
| 域名解析 | /etc/hosts（本地）/ 云 DNS（生产） | mkc.local 等 |

### 3.6 DevOps / CI/CD

| 领域 | 选型 | 说明 |
|---|---|---|
| 代码托管 | GitHub | 仓库、Issues、Projects、Actions |
| CI | GitHub Actions | 按服务独立 workflow |
| 网关 CI | golangci-lint + go test -race + coverage | 质量门禁 |
| AI CI | ruff + black + mypy + pytest-cov | 代码质量 |
| 客户端 CI | flutter analyze + flutter test + build apk |  |
| 容器化 | Docker + Dockerfile | 多阶段构建 |
| 分支模型 | GitHub Flow | main 保护 + PR review |
| 提交规范 | Conventional Commits | feat/fix/refactor/docs/test/chore/perf/ci |

### 3.7 可观测性

| 领域 | 选型 | 说明 |
|---|---|---|
| Trace | OpenTelemetry + Jaeger | 全链路追踪 |
| Metrics | Prometheus | 指标采集 |
| 日志 | Grafana Loki（预留） | 日志聚合 |
| 可视化 | Grafana | 监控面板 |

### 3.8 安全

| 领域 | 选型 | 说明 |
|---|---|---|
| 认证 | JWT + Redis Session | access_token 15 分钟 + refresh_token 7 天 |
| 密码存储 | bcrypt | 强哈希 |
| 内部调用 | X-Internal-Key | Gateway ↔ AI Service 内部鉴权 |
| 限流 | Redis Token Bucket | 用户维度 + 路径维度 |
| Secret | 环境变量 / K8s Secret | 禁止硬编码 |

---

## 4. 版本兼容性与约束

| 组件 | 最低版本 | 关键约束 |
|---|---|---|
| Flutter | 3.22 | 支持 Riverpod 2.5+ 和最新 go_router |
| Go | 1.22 | 支持标准库新特性 |
| Python | 3.11 | faster-whisper 和 torch 兼容性 |
| MySQL | 8.0 | 支持 JSON 函数和 utf8mb4 |
| Redis | 7.0 | Celery 5.4+ 推荐 |
| Kubernetes | 1.29 | IngressClass API 稳定 |

---

## 5. 选型演进路线

| 阶段 | 时间 | 调整 |
|---|---|---|
| Sprint 0-1 | 当前 | GORM AutoMigrate、Docker Desktop K8s、单节点中间件 |
| Sprint 2 | 后续 | 引入 golang-migrate 替代 AutoMigrate |
| Sprint 3+ | 后续 | Milvus standalone → cluster，引入 Prometheus/Grafana |
| 生产准备 | 后续 | 云 RDS/Redis/对象存储、External Secrets、cert-manager |

---

## 6. 相关文档

- [TECH_S0-1_github_repo_init.md](./TECH_S0-1_github_repo_init.md)
- [TECH_S0-2_local_k8s_manifests.md](./TECH_S0-2_local_k8s_manifests.md)
- [TECH_S0-3_github_actions_ci.md](./TECH_S0-3_github_actions_ci.md)
- [TECH_S0-4_database_schema_migration.md](./TECH_S0-4_database_schema_migration.md)
- [TECH_S0-5_api_interface_design.md](./TECH_S0-5_api_interface_design.md)
- [TECH_S0-6_flutter_project_skeleton.md](./TECH_S0-6_flutter_project_skeleton.md)
- [TECH_S0-7_go_gateway_skeleton.md](./TECH_S0-7_go_gateway_skeleton.md)
- [TECH_S0-8_python_ai_service_skeleton.md](./TECH_S0-8_python_ai_service_skeleton.md)
