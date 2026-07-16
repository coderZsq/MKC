# S5-8 测试用例：部署到 Kubernetes 集群并绑定域名

## 1. 范围与目标

验证 K8s manifests、Ingress、TLS、Secret、持久化、健康检查、回滚、在线 smoke 和 Web 部署适配。

## 2. 测试环境

- Kubernetes 1.28+
- kubectl
- Kustomize / Helm
- Ingress NGINX
- Cert-Manager
- 测试域名或本地域名映射

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-8-001 | Functional | Static | P0 | manifests 可渲染 | k8s 文件存在 | kubectl kustomize | 输出合法 YAML | PRD AC-1 |
| MKC-TC-S5-8-002 | Functional | Integration | P0 | Ingress 域名路由可访问 | DNS 配置完成 | curl 域名 | 返回 Client 或 API 响应 | PRD AC-2 |
| MKC-TC-S5-8-003 | Functional | Integration | P0 | HTTPS 证书有效 | Cert-Manager 已部署 | 访问 https 域名 | 证书有效 | PRD AC-2 |
| MKC-TC-S5-8-004 | Functional | Static | P0 | Secret/ConfigMap 分离 | manifests 存在 | 检查 YAML | 密钥走 Secret 模板 | PRD AC-3 |
| MKC-TC-S5-8-005 | Functional | Static | P1 | probe 和资源限制存在 | Deployment 存在 | 检查 YAML | readiness/liveness/resources 完整 | PRD AC-4 |
| MKC-TC-S5-8-006 | Functional | Integration | P1 | 主链路 smoke 通过 | 环境已部署 | 运行 smoke_prod.sh | 登录/上传/问答可用 | PRD AC-7 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-8-007 | Security | Static | P0 | 仓库无真实 Secret | manifests 存在 | 扫描密钥模式 | 无真实凭据 | PRD AC-3 |
| MKC-TC-S5-8-008 | Security | Integration | P1 | metrics/内部服务不公网暴露 | 集群部署 | 检查 Ingress | 仅公开必要入口 | 安全要求 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-8-009 | Negative | Integration | P1 | Pod 未就绪可定位 | 故意缺少配置 | kubectl describe | runbook 能定位 Secret/Probe 问题 | PRD AC-6 |
| MKC-TC-S5-8-010 | Negative | Integration | P1 | 回滚流程可执行 | 已部署旧版本 | 执行 rollout undo | 服务恢复旧版本 | PRD AC-6 |
| MKC-TC-S5-8-011 | Negative | Integration | P1 | PVC 重启后数据保留 | 写入测试数据 | 重启 Pod | 数据仍存在 | PRD AC-5 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-8-012 | Functional | Static | P1 | kubeconform/kubeval 通过 | manifests 存在 | 运行校验 | 0 issues | PRD AC-8 |
| MKC-TC-S5-8-013 | Functional | Static | P1 | 部署文档命令有效 | DEPLOYMENT 存在 | 抽检命令 | 命令路径正确 | PRD AC-6 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-8-014 | Compatibility | E2E | P0 | Flutter Web 静态资源可加载 | Web 已部署 | 打开域名 | 页面资源无 404 | PRD Web 端适配 |
| MKC-TC-S5-8-015 | Compatibility | E2E | P1 | SSE 经过 Ingress 可用 | Web 已部署 | 发起问答 | 流式回答不断流 | PRD Web 端适配 |

## 4. 测试执行清单

- [ ] K8s YAML 校验通过
- [ ] HTTPS 域名可访问
- [ ] smoke test 通过
- [ ] 回滚流程验证
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
