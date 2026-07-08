# S0-3 测试用例：GitHub Actions CI 流水线

## 1. 范围与目标

验证 `.github/workflows` 中三个 CI 工作流文件符合 PRD/TECH 设计，能够在 Push 与 Pull Request 触发，支持缓存、并发控制与分支保护，且不泄露任何 Secret。

## 2. 测试环境

- GitHub 仓库 `coderZsq/mkc` 已启用 Actions
- 已具备 PR 合并权限与分支保护设置权限
- 本地可选安装 `act` 用于本地验证

## 3. 测试用例

### 3.1 工作流文件存在性与结构

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-001 | Functional | Static | P0 | 三个工作流文件存在 | 仓库已克隆 | `ls .github/workflows/` | 存在 `ci-gateway.yml`、`ci-ai-service.yml`、`ci-client.yml` | PRD AC-1 |
| MKC-TC-S0-3-002 | Functional | Static | P0 | 工作流 YAML 语法有效 | 文件存在 | `yamllint .github/workflows/*.yml` 或 GitHub 在线编辑校验 | 无语法错误 | PRD AC-1 |
| MKC-TC-S0-3-003 | Functional | Static | P1 | 每个工作流包含 `name`、`on`、`jobs` | 文件存在 | 读取三个文件 | 均包含 name、触发事件、至少一个 job | GitHub Actions 规范 |
| MKC-TC-S0-3-004 | Functional | Static | P1 | 使用官方推荐的 action 版本 | 文件存在 | 检查 `uses:` 语句 | checkout@v4、setup-go@v5、setup-python@v5、flutter-action@v2 等 | PRD 工作流设计 |

### 3.2 触发条件

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-005 | Functional | E2E | P0 | Push 到任意分支触发所有工作流 | 已配置工作流 | 向 `feature/test-ci` 推送任意提交 | Actions 页面出现 ci-gateway / ci-ai-service / ci-client 运行记录 | PRD AC-5 |
| MKC-TC-S0-3-006 | Functional | E2E | P0 | Pull Request 触发所有工作流 | 已配置工作流 | 创建从 `feature/test-ci` 到 `main` 的 PR | PR 页面显示三个 checks 正在运行 | PRD AC-5 |
| MKC-TC-S0-3-007 | Boundary | E2E | P2 | Fork 仓库 PR 不消耗本仓库 Actions 分钟数 | Fork 仓库 | 从 Fork 提交 PR | 本仓库不运行 CI，或按 GitHub 默认行为运行（需确认项目设置） | GitHub 安全 |
| MKC-TC-S0-3-008 | Negative | E2E | P1 | 不相关路径变更不触发对应工作流 | 已配置 path filters | 修改 `docs/*.md` 后 PR | 仅触发不需要路径过滤的工作流，或按 TECH 设计不触发 Gateway/Python/Flutter CI | TECH |

### 3.3 ci-gateway.yml

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-009 | Functional | E2E | P0 | 设置 Go 1.22+ 环境 | 工作流存在 | 查看 `setup-go` 参数 | Go 版本 >= 1.22 | PRD 工作流设计 |
| MKC-TC-S0-3-010 | Functional | E2E | P1 | 缓存 Go modules | 工作流存在 | 查看 `actions/cache` 或 `cache: true` | 存在对 `~/go/pkg/mod` 的缓存配置 | PRD AC-6 |
| MKC-TC-S0-3-011 | Functional | E2E | P1 | 运行 golangci-lint | Gateway 代码存在 | 查看 jobs 步骤 | 包含 `golangci-lint run` 或对应 action | PRD 工作流设计 |
| MKC-TC-S0-3-012 | Functional | E2E | P0 | 运行 `go test ./...` | Gateway 代码存在 | 查看 jobs 步骤 | 包含 `go test ./... -race -coverprofile=coverage.out` | PRD 工作流设计 |
| MKC-TC-S0-3-013 | Functional | E2E | P0 | 编译检查通过 | Gateway 代码存在 | 查看 jobs 步骤 | 包含 `go build ./cmd/server` | PRD 工作流设计 |
| MKC-TC-S0-3-014 | Functional | E2E | P2 | 覆盖率报告生成（Sprint 1 启用阈值） | Gateway 测试存在 | 查看 jobs 输出 | 生成 coverage.out，后续可配置 80% 阈值 | PRD 工作流设计 |

### 3.4 ci-ai-service.yml

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-015 | Functional | E2E | P0 | 设置 Python 3.11 | 工作流存在 | 查看 `setup-python` 参数 | Python 版本为 3.11 | PRD 工作流设计 |
| MKC-TC-S0-3-016 | Functional | E2E | P1 | 安装生产与开发依赖 | AI Service 代码存在 | 查看 jobs 步骤 | 先 `pip install -r requirements.txt`，再 `pip install -r requirements-dev.txt` | PRD 工作流设计 |
| MKC-TC-S0-3-017 | Functional | E2E | P1 | 运行 ruff lint | AI Service 代码存在 | 查看 jobs 步骤 | 包含 `ruff check .` | PRD 工作流设计 |
| MKC-TC-S0-3-018 | Functional | E2E | P1 | 运行 black 格式检查 | AI Service 代码存在 | 查看 jobs 步骤 | 包含 `black --check .` | PRD 工作流设计 |
| MKC-TC-S0-3-019 | Functional | E2E | P2 | 运行 mypy 类型检查 | AI Service 代码存在 | 查看 jobs 步骤 | 包含 `mypy app`（可选） | PRD 工作流设计 |
| MKC-TC-S0-3-020 | Functional | E2E | P0 | 运行 pytest | AI Service 代码存在 | 查看 jobs 步骤 | 包含 `pytest --cov=app --cov-report=term-missing` | PRD 工作流设计 |

### 3.5 ci-client.yml

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-021 | Functional | E2E | P0 | 设置 Flutter stable | 工作流存在 | 查看 `subosito/flutter-action` 参数 | channel 为 stable | PRD 工作流设计 |
| MKC-TC-S0-3-022 | Functional | E2E | P1 | 缓存 pub 依赖 | 工作流存在 | 查看 cache 配置 | 存在 `~/.pub-cache` 缓存 | PRD AC-6 |
| MKC-TC-S0-3-023 | Functional | E2E | P0 | 运行 `flutter pub get` | Client 代码存在 | 查看 jobs 步骤 | 包含 `flutter pub get` | PRD 工作流设计 |
| MKC-TC-S0-3-024 | Functional | E2E | P0 | 运行 `flutter analyze` | Client 代码存在 | 查看 jobs 步骤 | 包含 `flutter analyze` | PRD 工作流设计 |
| MKC-TC-S0-3-025 | Functional | E2E | P0 | 运行 `flutter test` | Client 代码存在 | 查看 jobs 步骤 | 包含 `flutter test` | PRD 工作流设计 |
| MKC-TC-S0-3-026 | Functional | E2E | P2 | 构建检查（debug apk） | Client 代码存在 | 查看 jobs 步骤 | 包含 `flutter build apk --debug`（可选） | PRD 工作流设计 |

### 3.6 并发控制与分支保护

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-027 | Functional | Static | P0 | 工作流配置并发控制 | 工作流存在 | 查看 concurrency 字段 | 包含 `group: ${{ github.workflow }}-${{ github.ref }}` 与 `cancel-in-progress: true` | PRD 技术要点 |
| MKC-TC-S0-3-028 | Functional | E2E | P1 | 同一分支多次推送时旧工作流被取消 | 已启用 concurrency | 连续两次快速 push 同一分支 | 第一次运行被取消，第二次继续运行 | PRD 技术要点 |
| MKC-TC-S0-3-029 | Security | E2E | P0 | `main` 分支保护要求 status checks 通过 | 仓库管理员权限 | Settings -> Branches | `main` 分支规则勾选 "Require status checks to pass before merging"，并选择三个 CI | PRD AC-6 |
| MKC-TC-S0-3-030 | Negative | E2E | P1 | CI 未通过时 PR 无法合并 | 分支保护已启用 | 创建一个会导致 CI 失败的 PR | 合并按钮灰化，提示 checks 未通过 | PRD AC-6 |
| MKC-TC-S0-3-031 | Functional | E2E | P2 | PR 模板被使用 | 创建 PR | 新建 PR | 自动填充 PR 描述模板 | .github/PULL_REQUEST_TEMPLATE.md |

### 3.7 Secret 与安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-032 | Security | Static | P0 | 工作流文件无硬编码密钥 | 工作流存在 | `grep -i "password\|secret\|token" .github/workflows/*.yml` | 仅出现 `${{ secrets.XXX }}` 或环境变量引用，无具体值 | 安全基线 |
| MKC-TC-S0-3-033 | Security | Static | P1 | 工作流权限最小化 | 工作流存在 | 查看 `permissions:` | 使用 `permissions: contents: read` 或按需最小权限 | GitHub 安全 |
| MKC-TC-S0-3-034 | Security | E2E | P2 | Dependabot 已启用 | 仓库设置 | Settings -> Security -> Dependabot | Dependabot alerts / security updates 开启 | TECH |
| MKC-TC-S0-3-035 | Security | E2E | P2 | Secret scanning 已启用 | 仓库设置 | Settings -> Security -> Secret scanning | Secret scanning 开启 | TECH |

### 3.8 本地验证（act）

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-036 | Functional | Integration | P2 | 使用 `act` 本地运行 ci-gateway | 已安装 act | `act -j test-gateway` | 本地容器内完成 lint/test/build | 工程最佳实践 |
| MKC-TC-S0-3-037 | Functional | Integration | P2 | 使用 `act` 本地运行 ci-ai-service | 已安装 act | `act -j test-ai-service` | 本地容器内完成 lint/test | 工程最佳实践 |
| MKC-TC-S0-3-038 | Functional | Integration | P2 | 使用 `act` 本地运行 ci-client | 已安装 act | `act -j test-client` | 本地容器内完成 analyze/test | 工程最佳实践 |

### 3.9 徽章与文档

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-039 | Functional | Static | P1 | README 包含 CI 徽章 | 仓库已克隆 | `grep -A1 "CI" README.md` | 包含三个 workflow badge 的 markdown | PRD AC-7 |
| MKC-TC-S0-3-040 | Functional | E2E | P2 | CI 徽章状态与实际一致 | CI 运行后 | 查看 README 渲染 | badge 显示 passing / failing 与 Actions 状态一致 | PRD AC-7 |

### 3.10 异常与边界

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-3-041 | Exception | E2E | P1 | 工作流步骤失败时日志清晰 | 注入一个 lint 错误 | Push | 失败 job 的日志显示具体文件与行号 | 工程最佳实践 |
| MKC-TC-S0-3-042 | Boundary | E2E | P2 | 依赖缓存命中时 CI 时间显著缩短 | 第二次运行 | 记录两次 CI 时长 | 第二次下载依赖步骤耗时明显降低 | PRD AC-6 |
| MKC-TC-S0-3-043 | Idempotency | E2E | P2 | 同一 commit 重跑 CI 结果一致 | CI 已通过 | 点击 Re-run jobs | 结果仍为通过 | 工程最佳实践 |
| MKC-TC-S0-3-044 | Concurrency | E2E | P2 | 多 PR 同时触发不互相阻塞 | 创建多个 PR | 观察 Actions 队列 | 工作流按并发策略排队或并行，不影响结果正确性 | PRD 技术要点 |

## 4. 测试执行清单

- [ ] 三个工作流文件存在且语法正确
- [ ] Push / PR 均触发 CI
- [ ] `main` 分支保护要求三个 status checks
- [ ] 工作流中无硬编码 Secret
- [ ] README 徽章可正常显示
- [ ] Dependabot 与 Secret scanning 已启用

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
