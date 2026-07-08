# MKC Test Case Suite

> 目标：为 Sprint 0 与 Sprint 1 提供专家级、全场景覆盖的测试用例集，作为手工测试、CI 验收与自动化回归的依据。
> 来源：各卡片的 PRD 与 TECH 文档，以及 S0-1/S0-2 的真实踩坑记录。

---

## 1. 测试用例约定

| 字段 | 说明 |
|---|---|
| 用例编号 | `MKC-TC-S0-{N}-{SEQ}` / `MKC-TC-S1-{N}-{SEQ}`，例如 `MKC-TC-S0-2-013`、`MKC-TC-S1-5-007` |
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
| S0-1 | GitHub 仓库与目录结构 | [TEST_S0-1_repo_governance.md](./TEST_S0-1_repo_governance.md) | [PRD_S0-1](../prd/PRD_S0-1_github_repo_init.md) | [TECH_S0-1](../tech/TECH_S0-1_github_repo_init.md) |
| S0-2 | 本地 K8s 开发环境 | [TEST_S0-2_local_k8s.md](./TEST_S0-2_local_k8s.md) | [PRD_S0-2](../prd/PRD_S0-2_local_k8s_manifests.md) | [TECH_S0-2](../tech/TECH_S0-2_local_k8s_manifests.md) |
| S0-3 | GitHub Actions CI | [TEST_S0-3_ci_pipeline.md](./TEST_S0-3_ci_pipeline.md) | [PRD_S0-3](../prd/PRD_S0-3_github_actions_ci.md) | [TECH_S0-3](../tech/TECH_S0-3_github_actions_ci.md) |
| S0-4 | 数据库 Schema & Migration | [TEST_S0-4_database_schema.md](./TEST_S0-4_database_schema.md) | [PRD_S0-4](../prd/PRD_S0-4_database_schema_migration.md) | [TECH_S0-4](../tech/TECH_S0-4_database_schema_migration.md) |
| S0-5 | API 接口设计 | [TEST_S0-5_api_design.md](./TEST_S0-5_api_design.md) | [PRD_S0-5](../prd/PRD_S0-5_api_interface_design.md) | [TECH_S0-5](../tech/TECH_S0-5_api_interface_design.md) |
| S0-6 | Flutter 项目骨架 | [TEST_S0-6_flutter_skeleton.md](./TEST_S0-6_flutter_skeleton.md) | [PRD_S0-6](../prd/PRD_S0-6_flutter_project_skeleton.md) | [TECH_S0-6](../tech/TECH_S0-6_flutter_project_skeleton.md) |
| S0-7 | Go Gateway 项目骨架 | [TEST_S0-7_gateway_skeleton.md](./TEST_S0-7_gateway_skeleton.md) | [PRD_S0-7](../prd/PRD_S0-7_go_gateway_skeleton.md) | [TECH_S0-7](../tech/TECH_S0-7_go_gateway_skeleton.md) |
| S0-8 | Python AI Service 项目骨架 | [TEST_S0-8_ai_service_skeleton.md](./TEST_S0-8_ai_service_skeleton.md) | [PRD_S0-8](../prd/PRD_S0-8_python_ai_service_skeleton.md) | [TECH_S0-8](../tech/TECH_S0-8_python_ai_service_skeleton.md) |
| S1-1 | 用户注册/登录 API | [TEST_S1-1_user_auth_api.md](./TEST_S1-1_user_auth_api.md) | [PRD_S1-1](../prd/PRD_S1-1_user_auth_api.md) | [TECH_S1-1](../tech/TECH_S1-1_user_auth_api.md) |
| S1-2 | Flutter 登录/注册页面 | [TEST_S1-2_flutter_auth_pages.md](./TEST_S1-2_flutter_auth_pages.md) | [PRD_S1-2](../prd/PRD_S1-2_flutter_auth_pages.md) | [TECH_S1-2](../tech/TECH_S1-2_flutter_auth_pages.md) |
| S1-3 | 文件上传 API | [TEST_S1-3_file_upload_api.md](./TEST_S1-3_file_upload_api.md) | [PRD_S1-3](../prd/PRD_S1-3_file_upload_api.md) | [TECH_S1-3](../tech/TECH_S1-3_file_upload_api.md) |
| S1-4 | Flutter 文件选择/上传页面 | [TEST_S1-4_flutter_upload_page.md](./TEST_S1-4_flutter_upload_page.md) | [PRD_S1-4](../prd/PRD_S1-4_flutter_upload_page.md) | [TECH_S1-4](../tech/TECH_S1-4_flutter_upload_page.md) |
| S1-5 | 任务创建与状态查询 API | [TEST_S1-5_task_status_api.md](./TEST_S1-5_task_status_api.md) | [PRD_S1-5](../prd/PRD_S1-5_task_status_api.md) | [TECH_S1-5](../tech/TECH_S1-5_task_status_api.md) |
| S1-6 | Flutter 任务中心页面 | [TEST_S1-6_flutter_task_center.md](./TEST_S1-6_flutter_task_center.md) | [PRD_S1-6](../prd/PRD_S1-6_flutter_task_center.md) | [TECH_S1-6](../tech/TECH_S1-6_flutter_task_center.md) |
| S1-7 | SSE/WebSocket 任务进度推送 | [TEST_S1-7_task_progress_push.md](./TEST_S1-7_task_progress_push.md) | [PRD_S1-7](../prd/PRD_S1-7_task_progress_push.md) | [TECH_S1-7](../tech/TECH_S1-7_task_progress_push.md) |

---

## 3. 测试金字塔（Sprint 0 / Sprint 1）

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
| 用户认证 | S1-1 | S1-2/S1-3/S1-5/S1-6/S1-7 | 登录后获取 JWT，后续接口依赖认证 |
| 文件上传 | S1-3 | S1-4 | 上传页依赖上传 API |
| 任务管理 | S1-5 | S1-6/S1-7 | 任务中心与 SSE 依赖任务 API |
| 任务中心 | S1-6 | S1-7 | SSE 在任务中心页面订阅进度 |

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
