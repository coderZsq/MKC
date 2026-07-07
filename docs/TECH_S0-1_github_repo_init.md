# 技术文档：[S0-1] GitHub 仓库治理与目录结构设计

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 级别：架构师/技术负责人  
> 关联 PRD：[PRD_S0-1_github_repo_init.md](./PRD_S0-1_github_repo_init.md)

---

## 1. 文档目标

本文档定义多媒体 AI 知识库助手（MKC）项目的 GitHub 仓库治理策略、目录结构、分支模型、提交规范、看板配置和安全基线。目标是为单人或多协作者开发提供可持续演进的工程化基础。

---

## 2. 仓库治理策略

### 2.1 仓库可见性与权限

| 项 | 决策 | 说明 |
|---|---|---|
| 可见性 | Public | 便于简历展示、GitHub Actions 免费 Runner、社区参考 |
| 分支保护 | main 分支强制保护 | 禁止直接 push，所有改动通过 PR |
| PR Review | 单人项目可自 Review | 合并前必须 CI 全绿 |
| License | MIT | 开源友好，简历项目常用 |

### 2.2 分支模型：GitHub Flow（简化版）

```
main (production ready)
  │
  ├── feature/S0-1-init-repo
  ├── feature/S1-1-auth-api
  ├── feature/S2-1-asr-integration
  └── hotfix/fix-login-token
```

**分支命名规范**：
- `feature/{sprint-id}-{short-description}`，例如 `feature/S0-1-init-repo`
- `hotfix/{description}`，用于紧急修复
- `docs/{description}`，用于纯文档更新

**工作流**：
1. 从 `main` 切出 feature 分支
2. 本地开发并提交
3. Push 到远程，创建 Pull Request
4. CI 通过后自 Review，合并到 `main`
5. 合并后删除远程 feature 分支

### 2.3 Commit 规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type 类型**：

| type | 用途 |
|---|---|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式调整（不影响逻辑） |
| refactor | 重构 |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/工具链/依赖更新 |
| ci | CI/CD 配置 |

**scope 约定**：
- `client`：Flutter 前端
- `gateway`：Go 网关
- `ai-service`：Python AI 服务
- `infra`：基础设施
- `docs`：文档

**示例**：
```
feat(gateway): implement user registration API

- add /api/v1/auth/register endpoint
- add bcrypt password hashing
- add user repository and service layer

Closes #123
```

---

## 3. 目录结构设计

### 3.1 设计原则

- **按服务划分一级目录**：client、gateway、ai-service 独立演进，独立 CI
- **基础设施独立管理**：infra 目录集中 K8s、脚本、部署配置
- **文档与代码分离**：docs 目录存放 PRD、架构图、API 文档
- **避免跨服务引用**：各服务通过 HTTP/gRPC/消息队列交互，不直接共享代码

### 3.2 完整目录树

```
mkc/
├── .github/
│   ├── workflows/                  # CI/CD 工作流
│   │   ├── ci-gateway.yml
│   │   ├── ci-ai-service.yml
│   │   ├── ci-client.yml
│   │   └── cd-deploy.yml           # Sprint 5 添加
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── client/                         # Flutter 前端
│   ├── android/
│   ├── ios/
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app.dart
│   │   ├── config/
│   │   ├── data/
│   │   ├── domain/
│   │   ├── presentation/
│   │   └── shared/
│   ├── test/
│   ├── web/                        # Sprint 5 适配
│   ├── pubspec.yaml
│   ├── analysis_options.yaml
│   └── README.md
├── gateway/                        # Go 网关服务
│   ├── cmd/
│   │   └── server/
│   │       └── main.go
│   ├── internal/
│   │   ├── config/
│   │   ├── handler/
│   │   ├── middleware/
│   │   ├── model/
│   │   ├── repository/
│   │   ├── router/
│   │   └── service/
│   ├── pkg/
│   │   ├── response/
│   │   ├── errors/
│   │   └── utils/
│   ├── config/
│   │   ├── config.yaml
│   │   └── config.example.yaml
│   ├── migrations/
│   ├── scripts/
│   ├── Dockerfile
│   ├── go.mod
│   ├── go.sum
│   ├── Makefile
│   └── README.md
├── ai-service/                     # Python AI 服务
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   └── extensions.py
│   ├── celery_workers/
│   │   ├── celery_app.py
│   │   └── tasks/
│   ├── config/
│   ├── models/                     # 模型权重目录（gitignore）
│   ├── notebooks/                  # 实验性 notebook（可选）
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── celeryconfig.py
│   ├── Makefile
│   └── README.md
├── infra/                          # 基础设施
│   ├── k8s/
│   │   ├── namespaces/
│   │   ├── nginx-ingress/
│   │   ├── cert-manager/
│   │   ├── mysql/
│   │   ├── redis/
│   │   ├── minio/
│   │   ├── milvus/
│   │   ├── jaeger/
│   │   ├── gateway/
│   │   └── ai-service/
│   ├── scripts/
│   │   ├── local-up.sh
│   │   ├── local-down.sh
│   │   └── port-forward.sh
│   └── README.md
├── docs/                           # 项目文档
│   ├── PRD_multimedia_knowledge_assistant.md
│   ├── AGILE_plan_multimedia_knowledge_assistant.md
│   ├── architecture.md             # 系统架构图与说明
│   ├── api/
│   │   ├── openapi.yaml
│   │   └── api-design.md
│   ├── database-schema.md
│   └── runbooks/                   # 运维手册
│       └── troubleshooting.md
├── .gitignore
├── .editorconfig
├── LICENSE
└── README.md
```

### 3.3 各目录职责边界

| 目录 | 职责 | 不允许做的事 |
|---|---|---|
| `client/` | 用户界面、状态管理、本地存储 | 直接调用 MySQL/MinIO |
| `gateway/` | API 聚合、认证鉴权、业务编排、数据持久化 | 执行 AI 推理、文件解析 |
| `ai-service/` | AI 推理、异步任务、向量检索、RAG | 直接暴露公网入口 |
| `infra/` | K8s manifests、部署脚本、基础设施配置 | 包含业务代码 |
| `docs/` | 设计文档、API 文档、运维手册 | 包含可执行代码 |

---

## 4. .gitignore 设计

```gitignore
# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp
*.swo

# Env / Secrets
.env
.env.local
*.secret.yaml
*.secret.yml
secrets/

# Flutter / Dart
client/.dart_tool/
client/.packages
client/build/
client/.flutter-plugins
client/.flutter-plugins-dependencies
client/.pub-cache/
client/.pub/
client/pubspec.lock

# Go
gateway/bin/
gateway/vendor/
gateway/*.exe
gateway/coverage.out

# Python
ai-service/.venv/
ai-service/__pycache__/
ai-service/*.pyc
ai-service/.pytest_cache/
ai-service/.mypy_cache/
ai-service/htmlcov/
ai-service/.coverage
ai-service/*.egg-info/
ai-service/dist/
ai-service/build/

# Models / Data
ai-service/models/*
!ai-service/models/.gitkeep
*.bin
*.pt
*.pth
*.onnx
*.safetensors

# K8s / Infra
infra/k8s/**/*-secret.yaml
infra/k8s/**/secret*.yaml

# Logs
*.log
logs/
```

---

## 5. GitHub Project 看板配置

### 5.1 列定义

| 列 | 用途 |
|---|---|
| Backlog | 待排期需求 |
| To Do | 本 Sprint 待开始 |
| In Progress | 进行中 |
| Review / Test | 自测/联调/代码审查 |
| Done | 已完成 |

### 5.2 字段定义

| 字段 | 类型 | 说明 |
|---|---|---|
| Sprint | Single select | S0 / S1 / S2 / S3 / S4 / S5 |
| Story Points | Number | 1, 2, 3, 5, 8, 13 |
| Epic | Single select | E0-E12 |
| Priority | Single select | Must / Should / Could |
| Status | Single select | 与列同步 |
| Assignee | 默认自己 | |

### 5.3 自动化规则

- PR 与 Issue 关联时，自动移动到 Review / Test
- PR 合并后，自动移动到 Done
- Issue 关闭时，自动移动到 Done

---

## 6. PR 与 Issue 模板

### 6.1 PR 模板

```markdown
## 变更摘要

## 关联 Issue
Closes #

## 测试说明
- [ ] 单元测试通过
- [ ] 本地手动验证通过
- [ ] CI 通过

## 影响范围
```

### 6.2 Issue 模板

- Bug Report：复现步骤、期望行为、实际行为、环境信息
- Feature Request：背景、目标、验收标准、依赖任务

---

## 7. 安全基线

| 项 | 要求 |
|---|---|
| Secret 检测 | 启用 GitHub secret scanning |
| 依赖漏洞 | 启用 Dependabot alerts |
| 分支保护 | main 分支禁止 force push，要求 PR + CI |
| 代码审查 | 单人项目至少自 Review |
| 敏感文件 | `.env`、`*secret.yaml` 必须 gitignore |
| License 合规 | 记录所有依赖许可证 |

---

## 8. README 骨架

```markdown
# MKC - Multimedia AI Knowledge Companion

基于 Flutter + Go + Python 的多媒体 AI 知识库助手。

## 核心能力
- MP3 转录为 SRT 与文本
- PDF 解析为结构化文本
- 基于 RAG 的知识库问答
- 多轮 SSE 流式对话

## 技术栈
- 前端：Flutter + Clean Architecture + Riverpod
- 网关：Go + Gin + GORM + MySQL + Redis
- AI 服务：Python + Flask + Celery + LangGraph + LlamaIndex
- 基础设施：Kubernetes + nginx-ingress + MinIO + Milvus

## 快速开始
见 [docs/](./docs/) 目录。

## 目录结构
见 [技术文档 TECH_S0-1](./TECH_S0-1_github_repo_init.md)。

## License
MIT
```

---

## 9. 演进路线

| 阶段 | 仓库治理增强 |
|---|---|
| Sprint 0 | 基础目录、CI、看板 |
| Sprint 3 | 引入 API 变更日志（CHANGELOG.md） |
| Sprint 5 | 引入 Release Drafter、版本标签、容器镜像版本管理 |
| 上线后 | 引入 CODEOWNERS、多协作者权限分级 |

---

## 10. 检查清单

- [ ] 仓库创建并配置分支保护
- [ ] .gitignore 覆盖所有服务
- [ ] GitHub Project 看板配置完成
- [ ] Issue/PR 模板添加
- [ ] README 骨架编写完成
- [ ] 第一条 commit 提交成功
