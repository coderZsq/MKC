# MKC Sprint 0 Test Case Suite

> 目标：为 S0-1 ~ S0-8 提供专家级、全场景覆盖的测试用例集，作为手工测试、CI 验收与自动化回归的依据。
> 来源：各卡片的 PRD 与 TECH 文档，以及 S0-1/S0-2 的真实踩坑记录。

---

## 1. 测试用例约定

| 字段 | 说明 |
|---|---|
| 用例编号 | `MKC-TC-S0-{N}-{SEQ}`，例如 `MKC-TC-S0-2-013` |
| 测试维度 | Functional / Security / Negative / Boundary / Exception / Concurrency / Performance / Observability / Compatibility |
| 测试级别 | Static / Unit / Integration / E2E / Contract |
| 优先级 | P0 = 阻塞发布；P1 = 必须修复；P2 = 建议修复 |
| 前提条件 | 执行该用例前必须满足的环境与数据状态 |
| 执行步骤 | `Given / When / Then` 或编号步骤 |
| 预期结果 | 可观测、可断言的通过标准 |
| 关联需求 | 对应 PRD / TECH 的验收标准或章节 |

---

## 2. 文档清单

| 卡片 | 任务 | 测试用例文件 | 关联 PRD | 关联 TECH |
|---|---|---|---|---|
| S0-1 | GitHub 仓库与目录结构 | [S0-1-repo-governance.md](./S0-1-repo-governance.md) | [PRD_S0-1](../prd/PRD_S0-1_github_repo_init.md) | [TECH_S0-1](../tech/TECH_S0-1_github_repo_init.md) |
| S0-2 | 本地 K8s 开发环境 | [S0-2-local-k8s.md](./S0-2-local-k8s.md) | [PRD_S0-2](../prd/PRD_S0-2_local_k8s_manifests.md) | [TECH_S0-2](../tech/TECH_S0-2_local_k8s_manifests.md) |
| S0-3 | GitHub Actions CI | [S0-3-ci-pipeline.md](./S0-3-ci-pipeline.md) | [PRD_S0-3](../prd/PRD_S0-3_github_actions_ci.md) | [TECH_S0-3](../tech/TECH_S0-3_github_actions_ci.md) |
| S0-4 | 数据库 Schema & Migration | [S0-4-database-schema.md](./S0-4-database-schema.md) | [PRD_S0-4](../prd/PRD_S0-4_database_schema_migration.md) | [TECH_S0-4](../tech/TECH_S0-4_database_schema_migration.md) |
| S0-5 | API 接口设计 | [S0-5-api-design.md](./S0-5-api-design.md) | [PRD_S0-5](../prd/PRD_S0-5_api_interface_design.md) | [TECH_S0-5](../tech/TECH_S0-5_api_interface_design.md) |
| S0-6 | Flutter 项目骨架 | [S0-6-flutter-skeleton.md](./S0-6-flutter-skeleton.md) | [PRD_S0-6](../prd/PRD_S0-6_flutter_project_skeleton.md) | [TECH_S0-6](../tech/TECH_S0-6_flutter_project_skeleton.md) |
| S0-7 | Go Gateway 项目骨架 | [S0-7-gateway-skeleton.md](./S0-7-gateway-skeleton.md) | [PRD_S0-7](../prd/PRD_S0-7_go_gateway_skeleton.md) | [TECH_S0-7](../tech/TECH_S0-7_go_gateway_skeleton.md) |
| S0-8 | Python AI Service 项目骨架 | [S0-8-ai-service-skeleton.md](./S0-8-ai-service-skeleton.md) | [PRD_S0-8](../prd/PRD_S0-8_python_ai_service_skeleton.md) | [TECH_S0-8](../tech/TECH_S0-8_python_ai_service_skeleton.md) |

---

## 3. 测试金字塔（Sprint 0）

```
        /\\
       /  \\    E2E（本地 K8s 一键拉起 + 入口可达）
      /----\\
     /      \\  Integration（CI / DB migration / 服务依赖探测）
    /--------\\
   /          \\ Unit（health handler / 配置加载 / 响应封装）
  /--------------\\
 /  Static/Review \\（目录结构 / OpenAPI / lint / 安全扫描）
/--------------------\\
```

---

## 4. 入口与出口标准

### 入口标准
- 对应 S0 卡片已完成代码/配置提交。
- 本地环境（Docker Desktop K8s）可用，或已通过 CI 镜像准备。
- 各服务 README 中说明了启动与测试命令。

### 出口标准
- 所有 P0 用例通过。
- 所有 P1 用例通过或已记录缺陷并制定修复计划。
- 安全扫描无硬编码密钥、无敏感信息泄露。
- 测试覆盖率满足仓库 baseline（Sprint 0 至少有一条可运行的测试并通过；Sprint 1 起执行 80% 阈值）。

---

## 5. 关键跨卡依赖

| 依赖 | 上游卡片 | 下游卡片 | 说明 |
|---|---|---|---|
| 仓库目录 | S0-1 | 全部 | `client/`、`gateway/`、`ai-service/`、`infra/`、`docs/` 必须存在 |
| 本地 K8s | S0-2 | S0-4/S0-7/S0-8 | DB/Redis/MinIO/Milvus 为后续服务提供运行环境 |
| CI 工作流 | S0-3 | 全部 | PR 合并前必须通过的 status checks |
| DB Schema | S0-4 | S0-5/S0-7 | Gateway 模型与 migration 依赖 users/resources/tasks 等表 |
| API 契约 | S0-5 | S0-6/S0-7 | 前后端共享 OpenAPI 规范 |

---

## 6. 自动化建议

| 层级 | 推荐工具/命令 |
|---|---|
| Static | `tree`, `git ls-files`, `.gitignore` 检查，`detect-secrets`, `gitleaks` |
| Unit | `go test ./...`, `pytest`, `flutter test` |
| Integration | `kubectl`, `docker build`, `make migrate-up`, `act` |
| Contract | `swagger-codegen`, `openapi-generator-cli`, `schemathesis` |
| E2E | `local-up.sh` + 健康探测脚本 + Playwright/Flutter integration tests（后续补充） |

---

*本套件随 Sprint 推进持续维护；每新增一个接口或部署组件，应同步补充对应测试用例。*
