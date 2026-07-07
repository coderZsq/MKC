# PRD：[S0-3] 配置 GitHub Actions CI 流水线

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](../AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-3 |
| **任务名称** | 配置 GitHub Actions CI 流水线 |
| **所属史诗** | E0 基础设施 |
| **故事点** | 2 |
| **优先级** | Must |
| **依赖** | S0-1 仓库初始化 |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要在 GitHub 仓库中配置持续集成流水线，确保每次 Push 和 Pull Request 都能自动运行代码检查、单元测试和构建验证。该任务为后续代码质量和自动化部署提供保障。

---

## 验收标准（AC）

- [ ] `.github/workflows/` 目录下包含至少 3 个工作流文件
- [ ] `ci-gateway.yml`：Go 代码 lint、单元测试、编译检查
- [ ] `ci-ai-service.yml`：Python 代码 lint、单元测试
- [ ] `ci-client.yml`：Flutter `analyze` 和 `test`
- [ ] 工作流在 Push 到任意分支和 Pull Request 时自动触发
- [ ] CI 通过结果作为 PR 合并的必要条件（branch protection）
- [ ] 每个工作流都支持缓存依赖，减少执行时间
- [ ] README 中增加 CI 徽章（badges）

---

## 工作流设计

### 1. ci-gateway.yml

| 步骤 | 工具/命令 |
|---|---|
| 检出代码 | `actions/checkout@v4` |
| 设置 Go 环境 | `actions/setup-go@v5`，Go 1.22+ |
| 缓存 Go modules | `actions/cache@v4` |
| Lint | `golangci-lint` |
| 单元测试 | `go test ./... -race -coverprofile=coverage.out` |
| 覆盖率阈值 | ≥ 80%（Sprint 1 后启用） |
| 编译检查 | `go build ./cmd/server` |

### 2. ci-ai-service.yml

| 步骤 | 工具/命令 |
|---|---|
| 检出代码 | `actions/checkout@v4` |
| 设置 Python 环境 | `actions/setup-python@v5`，Python 3.11 |
| 安装依赖 | `pip install -r requirements.txt` 和 `requirements-dev.txt` |
| Lint | `ruff` 或 `flake8` |
| 格式化检查 | `black --check` |
| 类型检查（可选） | `mypy` |
| 单元测试 | `pytest --cov=app --cov-report=term-missing` |
| 覆盖率阈值 | ≥ 80%（Sprint 1 后启用） |

### 3. ci-client.yml

| 步骤 | 工具/命令 |
|---|---|
| 检出代码 | `actions/checkout@v4` |
| 设置 Flutter 环境 | `subosito/flutter-action@v2`，Flutter stable |
| 获取依赖 | `flutter pub get` |
| 代码分析 | `flutter analyze` |
| 单元测试 | `flutter test` |
| 构建检查（可选） | `flutter build apk --debug` |

---

## 工作流文件位置

```
.github/
└── workflows/
    ├── ci-gateway.yml
    ├── ci-ai-service.yml
    └── ci-client.yml
```

---

## 技术要点

- **并发控制**：使用 `concurrency` 避免同一分支多次提交排队冲突
  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```
- **分支保护**：在 GitHub 仓库设置中开启
  - Require status checks to pass before merging
  - 勾选 `ci-gateway`、`ci-ai-service`、`ci-client`
- ** secrets 管理**：CI 中不直接写密码，后续通过 GitHub Secrets 注入
- **缓存策略**：
  - Go：`~/go/pkg/mod`
  - Python：pip cache
  - Flutter：`~/.pub-cache`

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Flutter 在 GitHub Actions 中构建慢 | 影响反馈速度 | 仅运行 analyze 和 test，不构建 release 包 |
| Go/Python 测试依赖外部服务 | CI 不稳定 | Sprint 0 阶段先跑空测试或纯单元测试 |
| golangci-lint 配置复杂 | 初期 lint 大量报错 | 从基础规则开始，逐步收紧 |

---

## 备注

- Sprint 0 的 CI 以"流程跑通"为目标，测试用例可以在 Sprint 1 逐步补充
- 后续会增加 Docker 镜像构建和 K8s 部署流水线（Sprint 5）
- CI 徽章示例：
  ```markdown
  ![Gateway CI](https://github.com/coderZsq/mkc/actions/workflows/ci-gateway.yml/badge.svg)
  ```
