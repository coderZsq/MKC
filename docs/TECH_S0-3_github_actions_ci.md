# 技术文档：[S0-3] GitHub Actions CI/CD 流水线架构

> 版本：v1.0  > 日期：2026-07-06  > 作者：朱双泉  > 级别：架构师/DevOps 负责人  > 关联 PRD：[PRD_S0-3_github_actions_ci.md](./PRD_S0-3_github_actions_ci.md)

---

## 1. 文档目标

本文档定义 MKC 项目的 GitHub Actions 持续集成流水线架构，包括工作流设计、依赖缓存策略、代码质量门禁、安全检查、分支保护、Artifact 管理以及未来 CD 扩展路径。

---

## 2. CI 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                     GitHub Repository                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Push / PR  │  │  Push / PR  │  │      Push / PR      │  │
│  │   (client)  │  │  (gateway)  │  │    (ai-service)     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │             │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────────▼──────────┐  │
│  │ ci-client   │  │ ci-gateway  │  │   ci-ai-service     │  │
│  │  ├ analyze  │  │  ├ lint     │  │   ├ lint            │  │
│  │  ├ test     │  │  ├ test     │  │   ├ test            │  │
│  │  └ build    │  │  └ build    │  │   └ type-check      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │             │
│         └────────────────┴────────────────────┘             │
│                          │                                    │
│                   ┌──────▼──────┐                            │
│                   │  Branch     │                            │
│                   │  Protection │                            │
│                   │  (main)     │                            │
│                   └─────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 工作流设计

### 3.1 触发策略

```yaml
on:
  push:
    branches:
      - main
      - feature/**
  pull_request:
    branches:
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### 3.2 ci-gateway.yml

```yaml
name: Gateway CI

on:
  push:
    branches: [main, feature/**]
    paths:
      - 'gateway/**'
      - '.github/workflows/ci-gateway.yml'
  pull_request:
    branches: [main]
    paths:
      - 'gateway/**'
      - '.github/workflows/ci-gateway.yml'

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./gateway
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache-dependency-path: ./gateway/go.sum

      - name: Install golangci-lint
        uses: golangci/golangci-lint-action@v6
        with:
          version: v1.59
          working-directory: ./gateway

      - name: Download dependencies
        run: go mod download

      - name: Run tests
        run: go test ./... -race -coverprofile=coverage.out

      - name: Check coverage
        run: |
          go tool cover -func=coverage.out | grep total | awk '{print $3}'

      - name: Build
        run: go build -o bin/server ./cmd/server

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: gateway-coverage
          path: ./gateway/coverage.out
```

### 3.3 ci-ai-service.yml

```yaml
name: AI Service CI

on:
  push:
    branches: [main, feature/**]
    paths:
      - 'ai-service/**'
      - '.github/workflows/ci-ai-service.yml'
  pull_request:
    branches: [main]
    paths:
      - 'ai-service/**'
      - '.github/workflows/ci-ai-service.yml'

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./ai-service
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: |
            ./ai-service/requirements.txt
            ./ai-service/requirements-dev.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint with ruff
        run: ruff check .

      - name: Format check with black
        run: black --check .

      - name: Type check with mypy
        run: mypy app

      - name: Run tests
        run: pytest --cov=app --cov-report=term-missing --cov-report=xml

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: ai-service-coverage
          path: ./ai-service/coverage.xml
```

### 3.4 ci-client.yml

```yaml
name: Client CI

on:
  push:
    branches: [main, feature/**]
    paths:
      - 'client/**'
      - '.github/workflows/ci-client.yml'
  pull_request:
    branches: [main]
    paths:
      - 'client/**'
      - '.github/workflows/ci-client.yml'

jobs:
  analyze-and-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./client
    steps:
      - uses: actions/checkout@v4

      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.22.x'
          channel: 'stable'

      - name: Get dependencies
        run: flutter pub get

      - name: Analyze
        run: flutter analyze --fatal-infos

      - name: Run tests
        run: flutter test --coverage

      - name: Build APK (debug)
        run: flutter build apk --debug
```

---

## 4. 代码质量门禁

### 4.1 Gateway

| 检查项 | 工具 | 阈值 |
|---|---|---|
| Lint | golangci-lint | 无 ERROR |
| 测试 | go test | 全部通过 |
| 覆盖率 | go tool cover | ≥ 80%（Sprint 1 起） |
| 竞态检测 | -race | 无 DATA RACE |
| 编译 | go build | 成功 |

**golangci-lint 基础配置**：
```yaml
run:
  timeout: 5m
linters:
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - unused
    - gofmt
    - goimports
    - misspell
linters-settings:
  gofmt:
    simplify: true
```

### 4.2 AI Service

| 检查项 | 工具 | 阈值 |
|---|---|---|
| Lint | ruff | 无 ERROR |
| 格式化 | black | 全部通过 |
| 类型检查 | mypy | 无 ERROR |
| 测试 | pytest | 全部通过 |
| 覆盖率 | pytest-cov | ≥ 80%（Sprint 1 起） |

### 4.3 Client

| 检查项 | 工具 | 阈值 |
|---|---|---|
| 静态分析 | flutter analyze | 无 ERROR |
| 测试 | flutter test | 全部通过 |
| 构建 | flutter build apk | 成功 |

---

## 5. 缓存策略

### 5.1 Go Modules

`actions/setup-go@v5` 内置缓存，无需额外配置。

### 5.2 Python pip

`actions/setup-python@v5` 配合 `cache: 'pip'` 自动缓存。

### 5.3 Flutter

`subosito/flutter-action@v2` 自动缓存 SDK 和 pub 依赖。

---

## 6. 分支保护规则

在 GitHub 仓库 Settings → Branches 中配置：

```
Branch name pattern: main
[x] Require a pull request before merging
    [x] Require approvals: 1
[x] Require status checks to pass before merging
    [x] Gateway CI
    [x] AI Service CI
    [x] Client CI
[x] Require branches to be up to date before merging
[x] Restrict who can push to matching branches
    [ ] Allow force pushes: 禁止
    [ ] Allow deletions: 禁止
```

---

## 7. 安全扫描

### 7.1 Secret Scanning

GitHub 默认启用 secret scanning，检测到潜在 secret 会阻止 push。

### 7.2 Dependabot

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "gomod"
    directory: "/gateway"
    schedule:
      interval: "weekly"
  - package-ecosystem: "pip"
    directory: "/ai-service"
    schedule:
      interval: "weekly"
  - package-ecosystem: "pub"
    directory: "/client"
    schedule:
      interval: "weekly"
```

### 7.3 代码扫描（可选）

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'sarif'
    output: 'trivy-results.sarif'
```

---

## 8. Artifact 与报告

| Artifact | 来源 | 用途 |
|---|---|---|
| gateway-coverage | Go 测试 | 覆盖率追踪 |
| ai-service-coverage | pytest | 覆盖率追踪 |
| client-coverage | flutter test | 覆盖率追踪 |
| trivy-results.sarif | Trivy | 安全漏洞报告 |

---

## 9. PR 与 Issue 集成

### 9.1 自动关闭 Issue

PR 描述中写入：
```
Closes #123
```

合并后自动关闭关联 Issue。

### 9.2 状态同步

通过 GitHub Projects 工作流自动化：
- PR 创建 → Issue 移动到 Review / Test
- PR 合并 → Issue 移动到 Done

---

## 10. 未来 CD 扩展

Sprint 5 增加部署流水线：

```yaml
# .github/workflows/cd-deploy.yml
name: CD Deploy
on:
  push:
    branches: [main]
    tags: ['v*']
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker images
        run: |
          docker build -t mkc-gateway:${{ github.sha }} ./gateway
          docker build -t mkc-ai-service:${{ github.sha }} ./ai-service
      - name: Push to registry
        run: |
          echo ${{ secrets.REGISTRY_PASSWORD }} | docker login ...
          docker push mkc-gateway:${{ github.sha }}
      - name: Deploy to K8s
        run: |
          kubectl set image deployment/gateway gateway=mkc-gateway:${{ github.sha }}
```

---

## 11. 检查清单

- [ ] 三个 CI 工作流文件创建
- [ ] 触发路径正确配置
- [ ] 缓存策略生效
- [ ] 分支保护启用
- [ ] Dependabot 配置
- [ ] Secret scanning 启用
- [ ] CI 徽章加入 README
- [ ] 测试用例覆盖核心路径
