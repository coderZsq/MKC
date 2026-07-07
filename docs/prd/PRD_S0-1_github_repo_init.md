# PRD：[S0-1] 初始化 GitHub 仓库与目录结构

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](../AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-1 |
| **任务名称** | 初始化 GitHub 仓库与目录结构 |
| **所属史诗** | E0 基础设施 |
| **故事点** | 1 |
| **优先级** | Must |
| **依赖** | 无 |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要创建一个清晰的 GitHub 仓库和目录结构，让客户端、网关、AI 服务、基础设施配置和文档有明确的归属。该任务为整个项目的版本控制、协作开发和持续集成奠定基础。

---

## 验收标准（AC）

- [ ] GitHub 公开仓库 `mkc` 创建完成，并克隆到本地
- [ ] 仓库根目录包含 README.md，说明项目背景、技术栈、目录结构
- [ ] 目录结构包含 `client/`、`gateway/`、`ai-service/`、`infra/`、`docs/` 五个一级目录
- [ ] 每个一级目录下包含 `.gitkeep` 或基础子目录占位文件
- [ ] 根目录包含 `.gitignore`，覆盖 Flutter、Go、Python、Kubernetes、IDE 和临时文件
- [ ] 初始化 GitHub Project 看板，包含 Backlog / To Do / In Progress / Review / Done 五列
- [ ] 将 AGILE 计划中的 S0-S5 任务卡录入 GitHub Project
- [ ] 提交第一条 commit：`chore: init repo structure`

---

## 推荐目录结构

```
mkc/
├── .github/
│   └── workflows/            # GitHub Actions 流水线
├── client/                   # Flutter 前端
│   ├── android/
│   ├── ios/
│   ├── lib/
│   ├── test/
│   ├── pubspec.yaml
│   └── README.md
├── gateway/                  # Go 网关服务
│   ├── cmd/
│   ├── internal/
│   ├── pkg/
│   ├── config/
│   ├── migrations/
│   ├── go.mod
│   └── README.md
├── ai-service/               # Python AI 服务
│   ├── app/
│   ├── celery_workers/
│   ├── models/
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── infra/                    # 基础设施配置
│   ├── k8s/                  # Kubernetes manifests
│   ├── scripts/              # 部署与初始化脚本
│   └── README.md
├── docs/                     # 项目文档
│   ├── prd/                  # 产品需求文档
│   │   ├── PRD_multimedia_knowledge_assistant.md
│   │   └── PRD_S0-1_github_repo_init.md
│   ├── tech/                 # 技术文档
│   │   ├── TECH_STACK.md
│   │   └── TECH_S0-1_github_repo_init.md
│   ├── AGILE_plan_multimedia_knowledge_assistant.md
│   ├── architecture.md
│   ├── api/
│   │   ├── openapi.yaml
│   │   └── api-design.md
│   ├── database-schema.md
│   └── runbooks/
│       └── troubleshooting.md
├── .gitignore
├── LICENSE
└── README.md
```

---

## 技术要点

- **仓库可见性**：建议公开，便于简历展示与 GitHub Actions 免费额度
- **分支策略**：采用 `main` + `feature/*` 工作流，PR 合并前要求 CI 通过
- **.gitignore 覆盖范围**：
  - Flutter/Dart: `.dart_tool/`, `.packages`, `build/`, `pubspec.lock`
  - Go: `bin/`, `vendor/`, `*.exe`
  - Python: `__pycache__/`, `.venv/`, `*.pyc`, `.pytest_cache/`
  - K8s/Secret: `.env`, `*.secret.yaml`
  - IDE/OS: `.idea/`, `.vscode/`, `.DS_Store`
- **看板工具**：GitHub Projects，字段包含 Sprint、故事点、史诗、优先级、状态

---

## 阻塞风险

- 无

---

## 备注

- 本任务重点在仓库初始化，不涉及具体业务代码实现
- 第一条 commit 消息遵循 conventional commits：`chore: init repo structure`
- README 可先写骨架，技术细节随 Sprint 推进逐步补充
