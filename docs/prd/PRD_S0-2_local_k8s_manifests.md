# PRD：[S0-2] 搭建本地 K8s 开发环境并编写 manifests

> 版本：v1.0  
> 日期：2026-07-06  
> 作者：朱双泉  
> 关联文档：[PRD_multimedia_knowledge_assistant.md](./PRD_multimedia_knowledge_assistant.md)、[AGILE_plan_multimedia_knowledge_assistant.md](../AGILE_plan_multimedia_knowledge_assistant.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S0-2 |
| **任务名称** | 搭建本地 K8s 开发环境并编写 manifests |
| **所属史诗** | E0 基础设施 |
| **故事点** | 5 |
| **优先级** | Must |
| **依赖** | S0-1 仓库初始化 |
| **目标 Sprint** | Sprint 0 |

---

## 描述

作为开发者，我需要在本地搭建一套与生产环境一致的 Kubernetes 开发环境，并编写所有依赖服务的 K8s manifests。Sprint 0 结束时，应能通过 `kubectl apply -f infra/k8s/` 一键拉起整个基础依赖栈。

---

## 验收标准（AC）

- [ ] 本地 K8s 集群启动成功（minikube / k3d / kind 任选其一）
- [ ] `infra/k8s/` 目录下包含所有基础服务 manifest
- [ ] `kubectl apply -f infra/k8s/` 成功应用所有资源
- [ ] 所有 Pod 状态为 Running/Ready
- [ ] nginx-ingress-controller 部署完成，暴露 Gateway 服务
- [ ] MySQL、Redis、MinIO、Milvus、Jaeger 均可在集群内访问
- [ ] 提供 `infra/scripts/local-up.sh` 一键启动脚本和 `local-down.sh` 清理脚本
- [ ] 编写基础设施部署 README，说明本地启动步骤和依赖版本

---

## 基础设施清单

| 组件 | 用途 | 部署方式 | 备注 |
|---|---|---|---|
| nginx-ingress-controller | 七层入口，TLS 终止、路由、限流基础层 | Helm / 官方 manifest | 本地使用 NodePort 暴露 |
| cert-manager | 自动签发并续期 Let's Encrypt 证书 | Helm | 生产环境启用 ClusterIssuer |
| MySQL 8.x | 业务数据：用户、任务、会话、资源元信息 | StatefulSet + PVC | 单节点即可，生产换主从 |
| Redis 7.x | Session 存储、缓存、限流、Celery broker | Deployment + PVC | 持久化开启 AOF |
| MinIO | 对象存储：MP3/PDF/SRT/文本文件 | Deployment + PVC | 默认 bucket 自动创建 |
| Milvus 2.4.x | 向量检索与 Embedding 存储 | Helm / 官方 manifest | standalone 模式 |
| Jaeger | 分布式链路追踪（OpenTelemetry 后端） | All-in-one Deployment | 开发阶段足够 |

---

## Manifest 目录结构

```
infra/
├── k8s/
│   ├── namespaces/
│   │   └── mkc-dev.yaml          # 命名空间 mkc-dev
│   ├── nginx-ingress/
│   │   └── ingress-nginx.yaml    # nginx-ingress-controller
│   ├── cert-manager/
│   │   └── cert-manager.yaml     # cert-manager（可选）
│   ├── mysql/
│   │   ├── configmap.yaml        # my.cnf
│   │   ├── secret.yaml           # root 密码（占位，不提交真实密码）
│   │   ├── pvc.yaml
│   │   ├── statefulset.yaml
│   │   └── service.yaml
│   ├── redis/
│   │   ├── configmap.yaml
│   │   ├── secret.yaml
│   │   ├── deployment.yaml
│   │   ├── pvc.yaml
│   │   └── service.yaml
│   ├── minio/
│   │   ├── secret.yaml
│   │   ├── deployment.yaml
│   │   ├── pvc.yaml
│   │   ├── service.yaml
│   │   └── init-buckets-job.yaml
│   ├── milvus/
│   │   └── milvus-standalone.yaml
│   ├── jaeger/
│   │   └── jaeger-all-in-one.yaml
│   └── gateway/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── ingress.yaml
├── scripts/
│   ├── local-up.sh               # 一键启动本地环境
│   ├── local-down.sh             # 清理本地环境
│   └── port-forward.sh           # 本地调试端口转发
└── README.md
```

---

## 技术要点

### 本地集群选择

- **minikube**：兼容性好，资源占用可控，推荐 macOS/Windows
- **k3d**：轻量、启动快，适合 Linux/macOS
- **kind**：对 Docker 依赖强，适合 CI 场景

建议本地开发使用 **k3d** 或 **minikube**，配置至少：
- CPU：4 core
- Memory：8 GB
- Disk：30 GB

### 存储类

- 本地集群默认提供 `standard` StorageClass
- MySQL、Redis、MinIO 使用 PVC 持久化数据
- 生产环境迁移到云厂商托管存储（如 AWS EBS、阿里云 ESSD）

### Secret 管理

- 本地使用 Kubernetes Secret 明文占位（方便开发）
- 生产环境通过 External Secrets Operator 或云厂商 KMS 注入
- **严禁将真实密码提交到 Git**

### 网络访问

- 本地通过 `mkc.local` 或 `127.0.0.1.nip.io` 解析到 Ingress
- `/etc/hosts` 增加：
  ```
  127.0.0.1  mkc.local
  ```
- Ingress 规则示例：
  ```yaml
  rules:
    - host: mkc.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gateway
                port:
                  number: 80
  ```

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Milvus 资源占用过高 | 本地机器跑不起来 | 先用 standalone 最小配置；必要时 S3 先用 Chroma/Redis 向量替代 |
| Ingress 控制器安装失败 | Gateway 无法暴露 | 检查 NodePort 端口是否冲突，或使用 `kubectl port-forward` 临时调试 |
| PVC 无法绑定 | 数据库 Pod 起不来 | 确认本地集群 StorageClass 可用，StorageClass 名称写对 |

---

## 备注

- 本地环境以"能跑通"为首要目标，不追求高可用
- 所有 manifest 应标注 `app.kubernetes.io/part-of: mkc` 标签，便于资源管理
- 后续 Sprint 将逐步补充 Gateway、AI Service、Flutter Web 的部署 manifests
