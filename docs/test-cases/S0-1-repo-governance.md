# S0-1 测试用例：GitHub 仓库与目录结构

## 1. 范围与目标

验证 GitHub 仓库初始化、根目录结构、README、LICENSE、.gitignore、GitHub Project 看板、分支策略与第一次提交符合 PRD / TECH 要求。

## 2. 测试环境

- 本地已克隆仓库 `git@github.com:coderZsq/mkc.git`
- GitHub 仓库可见性为 Public
- 具备仓库 Settings 读取权限（检查 branch protection、Projects）

## 3. 测试用例

### 3.1 仓库基础信息

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-1-001 | Functional | Static | P0 | 仓库存在且为公开仓库 | 已登录 GitHub | 1. 访问 `https://github.com/coderZsq/mkc`；2. 查看仓库 Visibility | 仓库可访问，显示 Public 标识 | PRD AC-1 |
| MKC-TC-S0-1-002 | Functional | Static | P0 | 仓库已成功克隆到本地 | 本地环境已配置 git | 1. `git remote -v`；2. `git branch --show-current` | 存在 `origin` 指向 GitHub，`main` 为当前分支 | PRD AC-1 |
| MKC-TC-S0-1-003 | Functional | Static | P0 | 根 README.md 存在且包含关键信息 | 仓库已克隆 | 1. `ls README.md`；2. 阅读 README 内容 | 文件存在，包含项目背景、技术栈、目录结构说明 | PRD AC-2 |
| MKC-TC-S0-1-004 | Functional | Static | P1 | LICENSE 文件存在 | 仓库已克隆 | `ls LICENSE` | 存在 LICENSE 文件 | 工程最佳实践 |
| MKC-TC-S0-1-005 | Functional | Static | P1 | 首次提交消息符合 Conventional Commits | 仓库已初始化 | `git log --oneline --all` | 第一条 commit 为 `chore: init repo structure` | PRD AC-8 |
| MKC-TC-S0-1-006 | Negative | Static | P1 | 首次提交消息不符合规范时应被拒绝 | 假设 PR 审查阶段 | 检查最近提交信息是否包含 `feat:` / `fix:` / `chore:` 等合法 type | 无 `init`、`first commit` 等非法消息 | PRD AC-8 / 通用规范 |

### 3.2 目录结构

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-1-007 | Functional | Static | P0 | 五个一级目录全部存在 | 仓库已克隆 | `ls -d client gateway ai-service infra docs` | 五个目录均存在 | PRD AC-3 |
| MKC-TC-S0-1-008 | Negative | Static | P1 | 缺少任意一级目录导致结构不完整 | 执行目录检查 | 删除/重命名 `ai-service/` 后重新检查 | 检查脚本/人工判定失败 | PRD AC-3 |
| MKC-TC-S0-1-009 | Functional | Static | P0 | 每个一级目录包含占位文件或基础子目录 | 仓库已克隆 | `find client gateway ai-service infra docs -maxdepth 2 -name ".gitkeep" -o -name "README.md"` | 每个目录下至少存在一个 `.gitkeep` 或 `README.md` | PRD AC-4 |
| MKC-TC-S0-1-010 | Functional | Static | P1 | `.github` 目录包含 workflows 与模板 | 仓库已克隆 | `ls .github/workflows .github/ISSUE_TEMPLATE .github/PULL_REQUEST_TEMPLATE.md` | workflows 目录、ISSUE_TEMPLATE 目录、PR 模板均存在 | PRD 推荐目录结构 |
| MKC-TC-S0-1-011 | Boundary | Static | P2 | 目录层级与 PRD 推荐结构一致 | 仓库已克隆 | 对比实际 `tree -L 3` 输出与 PRD 目录树 | 关键路径（client/lib/...、gateway/cmd/...、ai-service/app/...、infra/k8s/...）与推荐结构一致 | PRD 推荐目录结构 |

### 3.3 .gitignore 与 Secret 管理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-1-012 | Security | Static | P0 | .gitignore 覆盖 Flutter / Go / Python / K8s / IDE 文件 | 仓库已克隆 | `cat .gitignore` | 包含 `.dart_tool/`、`.packages`、`build/`、`bin/`、`vendor/`、`__pycache__/`、`.venv/`、`.env`、`*.secret.yaml`、`.idea/`、`.vscode/`、`.DS_Store` | PRD AC-5 |
| MKC-TC-S0-1-013 | Security | Static | P0 | 仓库无硬编码密钥或真实密码 | 任意提交 | 1. `git log -p` 搜索 `password`、`token`、`secret`、`api_key`；2. 运行 `gitleaks detect --source .` | 无高置信度泄露 | 安全基线 |
| MKC-TC-S0-1-014 | Negative | Static | P1 | 提交 secret 文件后被检测阻断 | 模拟创建 `infra/k8s/mysql/secret.yaml` | 1. 写入真实密码；2. `git add`；3. 运行 pre-commit/secret 扫描 | 扫描工具报出高危并阻止提交 | 安全基线 |
| MKC-TC-S0-1-015 | Security | Static | P1 | `.env` 文件不会被 git 跟踪 | 仓库已克隆 | `git check-ignore -v .env` 或创建 `.env` 后 `git status` | `.env` 处于 untracked 但不会被 `git add -A` 意外提交（即 `.gitignore` 生效） | PRD AC-5 |
| MKC-TC-S0-1-016 | Security | Static | P1 | `*.secret.yaml` 文件不会被 git 跟踪 | 仓库已克隆 | `git check-ignore -v rendered.secret.yaml` | 匹配 `.gitignore` 规则 | PRD AC-5 |

### 3.4 GitHub Project 看板

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-1-017 | Functional | E2E | P0 | GitHub Project 看板存在且包含五列 | 仓库已创建 | 访问仓库 Projects 页面 | 存在 Project，包含 Backlog / To Do / In Progress / Review / Done 五列 | PRD AC-6 |
| MKC-TC-S0-1-018 | Functional | E2E | P1 | S0 ~ S5 任务卡已录入看板 | 看板已创建 | 在看板中搜索 `S0-1`、`S0-2` ... `S0-8` | 每个任务卡都有对应 Issue / Draft / Card | PRD AC-7 |
| MKC-TC-S0-1-019 | Functional | E2E | P2 | 看板字段包含 Sprint、故事点、史诗、优先级、状态 | 看板已创建 | 查看 Project 自定义字段 | 至少包含上述字段 | PRD 技术要点 |

### 3.5 分支策略与保护

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-1-020 | Functional | E2E | P1 | 默认分支为 `main` | 仓库已创建 | 查看仓库 Settings -> Branches | Default branch 为 `main` | PRD 技术要点 |
| MKC-TC-S0-1-021 | Security | E2E | P1 | `main` 分支开启保护规则 | 仓库管理员权限 | Settings -> Branches -> Branch protection rules | 存在针对 `main` 的规则，要求 PR 合并，勾选至少一个 status check（预留） | PRD 技术要点 / TECH |
| MKC-TC-S0-1-022 | Negative | E2E | P2 | 直接向 `main` 推送被阻止 | 普通协作者权限 | `git push origin main` | 收到 `pre-receive hook` 或权限拒绝，无法直接推送 | 分支保护 |
| MKC-TC-S0-1-023 | Functional | E2E | P2 | 允许 `feature/*` 分支推送并创建 PR | 普通协作者权限 | 1. `git checkout -b feature/test-branch`；2. 推送；3. 创建 PR | PR 创建成功，可被审查与合并 | GitHub Flow |

### 3.6 Conventional Commits 与提交范围

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-1-024 | Functional | Static | P1 | 提交历史使用 Conventional Commits 格式 | 仓库已有多个提交 | `git log --oneline` | 提交消息形如 `<type>: <description>`，允许使用 scope `client/gateway/ai-service/infra/docs` | 通用规范 |
| MKC-TC-S0-1-025 | Negative | Static | P1 | 非法提交消息在 PR 审查中被要求修正 | PR 列表 | 检查最近 10 条合并提交 | 无不包含 type 前缀或格式混乱的提交 | 通用规范 |
| MKC-TC-S0-1-026 | Boundary | Static | P2 | 提交 scope 符合仓库模块划分 | 仓库已有多个提交 | 统计 scope 分布 | 常见 scope 为 `client`、`gateway`、`ai-service`、`infra`、`docs` 或无 scope | 通用规范 |

### 3.7 兼容性与可复现性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-1-027 | Compatibility | Static | P2 | 仓库在不同操作系统下克隆后目录一致 | macOS / Linux / WSL | `git clone` 后执行目录检查 | 目录结构一致，无文件名大小写冲突 | PRD AC-3 |
| MKC-TC-S0-1-028 | Idempotency | Static | P2 | 重复执行目录检查脚本结果一致 | 仓库已克隆 | 连续运行 3 次检查脚本 | 结果相同，无非确定性文件差异 | 工程最佳实践 |
| MKC-TC-S0-1-029 | Observability | Static | P2 | README 说明如何运行测试/启动项目 | 仓库已克隆 | 检查 README | README 包含后续 S0 卡片的启动命令链接或说明 | PRD AC-2 |

## 4. 测试执行清单

- [ ] P0 用例全部通过
- [ ] P1 用例全部通过或已记录缺陷
- [ ] `gitleaks` / `detect-secrets` 扫描无告警
- [ ] `main` 分支保护规则已启用
- [ ] GitHub Project 看板字段与列配置完成

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
