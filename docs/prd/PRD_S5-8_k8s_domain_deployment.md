# PRD：[S5-8] 部署到 Kubernetes 集群并绑定域名

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S0-2_local_k8s_manifests.md](./PRD_S0-2_local_k8s_manifests.md)、[TECH_S0-2_local_k8s_manifests.md](../tech/TECH_S0-2_local_k8s_manifests.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-8 |
| **任务名称** | 部署到 Kubernetes 集群并绑定域名 |
| **所属史诗** | E12 部署上线 |
| **故事点** | 5 |
| **优先级** | Should |
| **依赖** | S0-2 本地 K8s manifests |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为开发者，我希望将 MKC 部署到可访问的 Kubernetes 集群，并通过 Ingress、域名和 Cert-Manager 提供 HTTPS 访问，以便项目达到在线 Demo 和生产级演示状态。本任务覆盖 Gateway、AI Service、Client、依赖服务、配置、Secret、健康检查和回滚流程。

---

## 验收标准（AC）

- [ ] **AC-1** 提供 K8s manifests 或 Helm/Kustomize 覆盖 Gateway、AI Service、Client 与依赖服务
- [ ] **AC-2** Ingress 绑定域名并启用 HTTPS 证书自动签发
- [ ] **AC-3** 使用 K8s Secret/ConfigMap 管理配置，镜像中不包含密钥
- [ ] **AC-4** Deployment 配置 readiness/liveness probe、资源 requests/limits 与滚动更新策略
- [ ] **AC-5** 数据服务持久化策略明确，MinIO/MySQL/Milvus 数据不因 Pod 重启丢失
- [ ] **AC-6** 提供部署、升级、回滚和排障 runbook
- [ ] **AC-7** 在线 Demo 主链路可完成登录、上传、处理、问答和引用查看
- [ ] **AC-8** 部署相关静态检查与 smoke test 通过

---

## 推荐目录结构

```text
infra/
└── k8s/
    ├── base/
    ├── overlays/
    │   ├── local/
    │   └── prod/
    ├── ingress/
    └── cert-manager/
docs/
└── DEPLOYMENT.md
scripts/
└── smoke_prod.sh
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Kubernetes | 1.28+ | 部署运行时 |
| Ingress NGINX | 1.x | 域名入口 |
| Cert-Manager | 1.x | TLS 证书 |
| Kustomize / Helm | latest | 环境差异管理 |
| kubectl | 1.28+ | 部署与排障 |

---

## 技术要点

- 使用 `prod` overlay 管理域名、镜像 tag、资源配额和证书 issuer。
- Secret 通过外部注入，仓库只提交 `.env.example` 或 sealed secret 模板。
- 客户端 Web 构建产物通过 Nginx 或静态服务容器暴露。
- smoke test 至少覆盖健康检查、登录接口、上传接口、AI Service 内部健康检查。
- 发布前记录镜像 tag，回滚时按 tag 恢复。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 域名或证书配置失败 | Demo 无法 HTTPS 访问 | 提供 DNS、Ingress、Certificate 分步排查 |
| 资源不足 | AI 服务或 Milvus 不稳定 | 设置 requests/limits，给重模型任务降级 |
| Secret 管理不当 | 密钥泄露 | 禁止提交真实 Secret，部署文档使用占位符 |

---

## Web 端适配

Flutter Web 需要配置正确的 API base URL、CORS、SSE 代理超时、文件上传大小限制与静态资源缓存策略。

---

## 备注

- 本卡是 Sprint 5 在线 Demo 的关键路径。
- 若云厂商资源暂不可用，可先以自管 K8s 或单节点集群完成同等验收。
