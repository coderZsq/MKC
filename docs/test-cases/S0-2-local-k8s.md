# S0-2 测试用例：本地 K8s 开发环境与 Manifests

## 1. 范围与目标

验证本地 Kubernetes 环境一键拉起、所有基础服务 manifests 正确性、Pod 就绪、Ingress/DNS 可达性、脚本鲁棒性，以及踩坑记录中提到的 9 类问题不再复发。

## 2. 测试环境

- Docker Desktop 已启用 Kubernetes（推荐 CPU 6 核 / 内存 12 GB）
- `kubectl` 可连接集群
- 已配置环境变量：`MYSQL_ROOT_PASSWORD`、`MYSQL_PASSWORD`、`REDIS_PASSWORD`、`MINIO_ROOT_PASSWORD`
- 可选：`envsubst` 未安装，用于验证 Python fallback

## 3. 测试用例

### 3.1 前置依赖与脚本静态检查

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-001 | Functional | Static | P0 | `local-up.sh` 存在且可执行 | 仓库已克隆 | `ls -l infra/scripts/local-up.sh` | 文件存在且具备执行权限 | PRD AC-7 / TECH |
| MKC-TC-S0-2-002 | Functional | Static | P0 | `local-down.sh` 存在且可执行 | 仓库已克隆 | `ls -l infra/scripts/local-down.sh` | 文件存在且具备执行权限 | PRD AC-7 |
| MKC-TC-S0-2-003 | Functional | Static | P1 | `port-forward.sh` 存在且可执行 | 仓库已克隆 | `ls -l infra/scripts/port-forward.sh` | 文件存在且具备执行权限 | PRD 目录结构 |
| MKC-TC-S0-2-004 | Functional | Static | P1 | `render-secrets.sh` 存在且可执行 | 仓库已克隆 | `ls -l infra/scripts/render-secrets.sh` | 文件存在且具备执行权限 | TECH / 博客 |
| MKC-TC-S0-2-005 | Functional | Static | P0 | 所有 K8s 服务目录包含有效 YAML | 仓库已克隆 | `find infra/k8s -name "*.yaml" -exec kubectl apply --dry-run=client -f {} \;` | 所有 YAML 通过 client-side 语法校验 | PRD AC-2 |
| MKC-TC-S0-2-006 | Security | Static | P0 | Secret 模板文件使用占位符而非真实值 | 仓库已克隆 | `grep -R "root-user\|root-password" infra/k8s/*/secret.yaml.tpl` | 模板中值为 `${MYSQL_ROOT_PASSWORD}` 等占位符，非硬编码 | PRD 技术要点 |

### 3.2 一键启动脚本（local-up.sh）

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-007 | Functional | E2E | P0 | 本地 K8s 未启动时脚本给出清晰错误 | Docker Desktop K8s 关闭 | `./infra/scripts/local-up.sh` | 脚本在第 1 步检查失败并提示启用 Kubernetes | PRD AC-1 |
| MKC-TC-S0-2-008 | Functional | E2E | P0 | 正常流程一键拉起全部服务 | 环境变量已设置，Docker Desktop K8s 开启 | `./infra/scripts/local-up.sh` | 脚本 8 步全部成功，最终提示 hosts 配置与常用命令 | PRD AC-7 |
| MKC-TC-S0-2-009 | Negative | E2E | P1 | 缺少必要环境变量时启动失败或生成无效 Secret | 不设置 `MINIO_ROOT_PASSWORD` | `./infra/scripts/local-up.sh` | `render-secrets.sh` 渲染出空值或脚本显式报错，不会继续应用 | 安全基线 |
| MKC-TC-S0-2-010 | Functional | E2E | P1 | 重复执行 `local-up.sh` 幂等 | 已执行过一次成功 | 再次运行 `./infra/scripts/local-up.sh` | 脚本再次成功，已存在资源被 `kubectl apply` 幂等更新 | 工程最佳实践 |
| MKC-TC-S0-2-011 | Boundary | E2E | P2 | 脚本在资源紧张机器上的超时行为 | 分配 4 核 / 8 GB 内存 | 运行 `./infra/scripts/local-up.sh` | Milvus 可能启动缓慢但最终在 600s 超时内 Ready，或给出明确超时错误 | PRD 阻塞风险 |
| MKC-TC-S0-2-012 | Compatibility | E2E | P2 | 脚本在 `envsubst` 缺失的 macOS 上仍可运行 | macOS 未安装 gettext | 运行 `./infra/scripts/local-up.sh` | 脚本使用 Python `os.path.expandvars` fallback 完成 Secret 渲染 | 博客坑 1 |

### 3.3 Secret 渲染

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-013 | Functional | Integration | P0 | `render-secrets.sh` 生成正确的 Secret YAML | 环境变量已设置 | `./infra/scripts/render-secrets.sh` | 在 `infra/k8s/*/secret.yaml` 生成包含正确 base64 值的 Secret | TECH |
| MKC-TC-S0-2-014 | Security | Integration | P0 | 渲染后的 `secret.yaml` 不被 git 跟踪 | 渲染后文件存在 | `git status --short` | `secret.yaml` 处于 untracked，且 `.gitignore` 匹配 | PRD 技术要点 |
| MKC-TC-S0-2-015 | Security | Static | P1 | 禁止提交渲染后的 secret.yaml | 模拟 git add secret.yaml | 运行 secret 扫描 | 工具报出潜在 secret 或人工审查拒绝合并 | 安全基线 |
| MKC-TC-S0-2-016 | Boundary | Integration | P2 | 环境变量含特殊字符时渲染正确 | `MYSQL_PASSWORD='p@ssw0rd!#$%'` | `./infra/scripts/render-secrets.sh` | Secret YAML 合法，`kubectl apply` 后解码值完全匹配 | 工程最佳实践 |

### 3.4 命名空间与标签

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-017 | Functional | Integration | P0 | `mkc-dev` 命名空间被创建 | 运行 local-up | `kubectl get namespace mkc-dev` | 命名空间存在 | PRD 目录结构 |
| MKC-TC-S0-2-018 | Functional | Integration | P1 | 资源标注 `app.kubernetes.io/part-of: mkc` | 运行 local-up | `kubectl get all -n mkc-dev -o jsonpath='{..metadata.labels}'` | 所有 Deployment/Service/Pod 均带有该标签 | PRD 备注 |
| MKC-TC-S0-2-019 | Functional | Integration | P1 | 基础服务目录可独立 apply | 命名空间已创建 | `kubectl apply -f infra/k8s/mysql/` 等 | 每个服务目录 apply 成功 | PRD AC-2 |

### 3.5 各组件健康检查

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-020 | Functional | E2E | P0 | nginx-ingress-controller Pod Ready | local-up 成功 | `kubectl get pods -n ingress-nginx -l app.kubernetes.io/component=controller` | Pod 状态为 `Running` 且 `Ready` | PRD AC-5 |
| MKC-TC-S0-2-021 | Functional | E2E | P0 | MySQL StatefulSet 就绪 | local-up 成功 | `kubectl get pods -n mkc-dev -l app=mysql` | Pod `1/1 Ready`，PVC 已绑定 | PRD AC-4 |
| MKC-TC-S0-2-022 | Functional | E2E | P0 | Redis Deployment 就绪且 AOF 持久化 | local-up 成功 | 1. Pod Ready；2. `kubectl exec` 查看 `redis-cli CONFIG GET appendonly` | `appendonly` 为 `yes` | PRD 基础设施清单 |
| MKC-TC-S0-2-023 | Functional | E2E | P0 | MinIO Deployment 就绪 | local-up 成功 | `kubectl get pods -n mkc-dev -l app=minio` | Pod `1/1 Ready`，Service `minio:9000` 可达 | PRD AC-4 |
| MKC-TC-S0-2-024 | Functional | E2E | P0 | MinIO 初始化 Job 完成且 bucket 存在 | local-up 成功 | `kubectl logs job/minio-init-buckets -n mkc-dev` | 日志显示 `a-bucket`、`mkc-uploads`、`mkc-outputs` 创建成功，且 `mkc-uploads` / `mkc-outputs` 启用 version | PRD 基础设施清单 / 博客坑 8 |
| MKC-TC-S0-2-025 | Functional | E2E | P0 | Milvus etcd 就绪 | local-up 成功 | `kubectl get pods -n mkc-dev -l app=milvus-etcd` | Pod `1/1 Ready` | PRD AC-4 |
| MKC-TC-S0-2-026 | Functional | E2E | P0 | Milvus standalone 就绪 | local-up 成功 | `kubectl get pods -n mkc-dev -l app=milvus` | Pod `1/1 Ready`，无 CrashLoopBackOff | PRD AC-4 / 博客坑 9 |
| MKC-TC-S0-2-027 | Functional | E2E | P0 | Jaeger all-in-one 就绪 | local-up 成功 | `kubectl get pods -n mkc-dev -l app=jaeger` | Pod `1/1 Ready` | PRD AC-4 |
| MKC-TC-S0-2-028 | Functional | E2E | P1 | Gateway Service 与 Ingress 存在 | local-up 成功 | `kubectl get svc gateway -n mkc-dev` 与 `kubectl get ingress -n mkc-dev` | Service 与 Ingress 均存在 | PRD AC-5 |

### 3.6 Ingress 与本地 DNS

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-029 | Functional | E2E | P0 | Ingress Controller 监听 80/443 | local-up 成功 | `kubectl get svc -n ingress-nginx` | 存在 LoadBalancer/NodePort Service，80 端口映射到本地 | PRD AC-5 |
| MKC-TC-S0-2-030 | Functional | E2E | P0 | `/etc/hosts` 配置后可访问 `mkc.local` | local-up 成功，hosts 已配置 | `curl -I http://mkc.local/health` | 返回 HTTP 200（Gateway 未部署时可能 502，但至少能路由到 Ingress） | PRD 技术要点 |
| MKC-TC-S0-2-031 | Functional | E2E | P1 | `minio.mkc.local` 可访问 MinIO Console | local-up 成功，hosts 已配置 | 浏览器访问 `http://minio.mkc.local:9001` | 打开 MinIO 登录页 | infra/README |
| MKC-TC-S0-2-032 | Functional | E2E | P1 | `jaeger.mkc.local` 可访问 Jaeger UI | local-up 成功，hosts 已配置 | 浏览器访问 `http://jaeger.mkc.local` | 打开 Jaeger UI | infra/README |
| MKC-TC-S0-2-033 | Negative | E2E | P2 | 未配置 hosts 时无法通过域名访问 | hosts 未配置 | `curl http://mkc.local/health` | 解析失败或返回非预期结果 | PRD 技术要点 |

### 3.7 端口转发脚本

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-034 | Functional | Integration | P1 | `port-forward.sh` 转发 MySQL/Redis/MinIO/Milvus/Jaeger 端口 | local-up 成功 | `./infra/scripts/port-forward.sh` | 本地 3306、6379、9000、9001、16686、19530 可连接对应服务 | infra/README |
| MKC-TC-S0-2-035 | Boundary | Integration | P2 | 端口被占用时给出明确提示 | 3306 已被占用 | `./infra/scripts/port-forward.sh` | 脚本提示端口冲突并退出或自动选择其他端口 | 工程最佳实践 |

### 3.8 清理脚本

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-036 | Functional | E2E | P0 | `local-down.sh` 删除 mkc-dev 与 ingress-nginx | local-up 成功 | `./infra/scripts/local-down.sh` | 两个命名空间被删除，Pod 全部终止 | PRD AC-7 |
| MKC-TC-S0-2-037 | Functional | E2E | P1 | `local-down.sh` 保留 Docker Desktop 集群 | local-up 成功 | 执行 local-down 后 `kubectl get nodes` | Kubernetes 集群仍然可用 | infra/README |
| MKC-TC-S0-2-038 | Idempotency | E2E | P2 | 重复执行 `local-down.sh` 不报错 | 已执行过一次 | 再次运行 `./infra/scripts/local-down.sh` | 脚本成功，提示命名空间已不存在或静默跳过 | 工程最佳实践 |

### 3.9 稳定性与踩坑回归

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-039 | Functional | E2E | P0 | ingress-nginx 使用国内镜像源且非只读根文件系统 | local-up 成功 | `kubectl get deployment ingress-nginx-controller -n ingress-nginx -o yaml` | image 为 `m.daocloud.io/...`，`readOnlyRootFilesystem` 为 false（本地），`runAsUser: 101` | 博客坑 2/4/5 |
| MKC-TC-S0-2-040 | Functional | E2E | P1 | ingress-nginx ClusterRole 包含 endpointslices / leases / events | local-up 成功 | `kubectl get clusterrole ingress-nginx -o yaml` | 规则包含 `discovery.k8s.io/endpointslices`、`coordination.k8s.io/leases`、`events` | 博客坑 6 |
| MKC-TC-S0-2-041 | Functional | E2E | P1 | ingress-nginx 探针路径为 `/healthz` 端口 10254 | local-up 成功 | `kubectl describe pod -n ingress-nginx -l component=controller` | liveness/readiness 路径为 `/healthz`，端口 10254 | 博客坑 7 |
| MKC-TC-S0-2-042 | Functional | E2E | P1 | 所有镜像前缀为 DaoCloud 国内源 | local-up 成功 | `kubectl get pods --all-namespaces -o jsonpath='{..image}'` | 所有镜像以 `docker.m.daocloud.io/`、`quay.m.daocloud.io/` 或 `m.daocloud.io/` 开头 | 博客坑 2/3 |
| MKC-TC-S0-2-043 | Functional | E2E | P0 | Milvus 未使用部分 ConfigMap 覆盖默认配置 | local-up 成功 | `kubectl get configmap -n mkc-dev` | 不存在自定义 `milvus.yaml` ConfigMap；配置通过环境变量注入 | 博客坑 9 |
| MKC-TC-S0-2-044 | Functional | E2E | P1 | 使用 Job 而非 `kubectl run -i` 创建 bucket | local-up 成功 | `kubectl get jobs -n mkc-dev` | 存在 `minio-init-buckets` Job 且已完成 | 博客坑 8 |

### 3.10 性能与并发

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-045 | Performance | E2E | P1 | 完整拉起时间可接受 | 干净环境 | 记录 `local-up.sh` 从执行到 `[8/8] Done!` 的时间 | 在推荐配置（6C12G）下 < 5 分钟 | 工程最佳实践 |
| MKC-TC-S0-2-046 | Concurrency | E2E | P2 | 多个用户同时运行 local-up 不互相破坏 | 两台机器或两个用户 | 分别在不同 Docker Desktop 实例运行 | 各自独立（本场景主要为本地单实例，CI 中应使用 kind/k3d 隔离） | 工程最佳实践 |
| MKC-TC-S0-2-047 | Stability | E2E | P2 | 服务运行 30 分钟无重启 | local-up 成功 | 持续观察 30 分钟 `kubectl get pods -n mkc-dev` | 所有 Pod Restart 计数为 0 | 工程最佳实践 |

### 3.11 安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S0-2-048 | Security | Static | P0 | 本地 Secret 未提交到 Git | 仓库任意提交 | `git log --all --full-history -- infra/k8s/*/secret.yaml` | 无 `secret.yaml` 提交记录 | 安全基线 |
| MKC-TC-S0-2-049 | Security | E2E | P1 | MySQL root 密码与业务用户密码分离 | local-up 成功 | `kubectl get secret mysql-secret -n mkc-dev -o jsonpath='{.data}'` | root 密码与 `MYSQL_PASSWORD` 不同 | TECH |
| MKC-TC-S0-2-050 | Security | E2E | P2 | Redis 未启用无密码访问 | local-up 成功 | `kubectl exec -it deployment/redis -n mkc-dev -- redis-cli AUTH wrongpass PING` | 返回 `WRONGPASS` | PRD Redis 配置 |

## 4. 测试执行清单

- [ ] P0 用例全部通过
- [ ] `local-up.sh` 在干净环境下可完整运行
- [ ] `local-down.sh` 可清理环境并保留集群
- [ ] 9 个踩坑点均能在测试用例中追溯到回归验证
- [ ] 无渲染后的 `secret.yaml` 进入 git 历史

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
