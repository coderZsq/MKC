# MKC Infrastructure

本地与生产基础设施配置，基于 Kubernetes。

## 目录结构

```
infra/
├── k8s/              # Kubernetes manifests
│   ├── namespaces/   # mkc-dev 命名空间
│   ├── nginx-ingress/# 本地 Ingress Controller
│   ├── cert-manager/ # 生产 TLS 自动签发（本地暂不需要）
│   ├── mysql/        # MySQL StatefulSet + ConfigMap + Secret
│   ├── redis/        # Redis Deployment + ConfigMap + Secret
│   ├── minio/        # MinIO Deployment + Secret + 初始化 Bucket Job
│   ├── milvus/       # Milvus standalone + etcd
│   ├── jaeger/       # Jaeger all-in-one
│   ├── gateway/      # Gateway Service + Ingress（Deployment 在 S0-7 补充）
│   └── ai-service/   # AI Service 部署（后续 Sprint 补充）
└── scripts/          # 本地部署脚本
    ├── local-up.sh
    ├── local-down.sh
    ├── port-forward.sh
    └── render-secrets.sh
```

## 依赖版本

| 组件 | 镜像版本 | 说明 |
|---|---|---|
| nginx-ingress-controller | `m.daocloud.io/registry.k8s.io/ingress-nginx/controller:v1.10.1` | 本地 Ingress Controller（国内网络镜像源） |
| MySQL | `docker.m.daocloud.io/library/mysql:8.0.37` | 业务数据库 |
| Redis | `docker.m.daocloud.io/library/redis:7.2-alpine` | 缓存 / Session / Broker |
| MinIO | `docker.m.daocloud.io/minio/minio:RELEASE.2024-05-10T01-41-38Z` | 对象存储 |
| MinIO Client | `docker.m.daocloud.io/minio/mc:latest` | 初始化 buckets |
| Milvus | `docker.m.daocloud.io/milvusdb/milvus:v2.4.1` | 向量检索 |
| etcd | `quay.m.daocloud.io/coreos/etcd:v3.5.14` | Milvus 元数据存储 |
| Jaeger | `docker.m.daocloud.io/jaegertracing/all-in-one:1.57` | 分布式链路追踪 |

> 注：当前镜像使用 DaoCloud 国内镜像源。如果你的网络可以直接访问 Docker Hub / Quay / registry.k8s.io，可将镜像替换为官方地址。

## 前置条件

- Docker Desktop 已安装并启用内置 Kubernetes
- `kubectl` 可正常连接集群：
  ```bash
  kubectl get nodes
  ```
- 已安装 `envsubst`（gettext 工具包，macOS 可通过 `brew install gettext` 安装）
- 推荐资源配置：CPU 6 核 / 内存 12 GB / 磁盘 50 GB

## 本地启动

```bash
./infra/scripts/local-up.sh
```

脚本会依次完成：

1. 检查 Docker Desktop Kubernetes 连接
2. 部署 nginx-ingress-controller
3. 创建 `mkc-dev` 命名空间
4. 渲染 Secret 模板
5. 应用 MySQL / Redis / MinIO / Milvus / Jaeger / Gateway manifests
6. 等待 MinIO bucket 初始化 Job 完成（默认创建 `a-bucket`、`mkc-uploads`、`mkc-outputs`）
7. 等待所有 Pod 就绪

## 本地 DNS

在 `/etc/hosts` 中追加：

```
127.0.0.1 mkc.local
127.0.0.1 minio.mkc.local
127.0.0.1 jaeger.mkc.local
```

访问入口：

| 服务 | 地址 |
|---|---|
| Gateway API | http://mkc.local |
| MinIO Console | http://minio.mkc.local:9001 |
| Jaeger UI | http://jaeger.mkc.local |

## 端口转发

如需在宿主机直接连接中间件：

```bash
./infra/scripts/port-forward.sh
```

默认转发：

| 服务 | 本地端口 |
|---|---|
| MySQL | 3306 |
| Redis | 6379 |
| MinIO S3 | 9000 |
| MinIO Console | 9001 |
| Jaeger UI | 16686 |
| Milvus | 19530 |

## 本地关闭

```bash
./infra/scripts/local-down.sh
```

该脚本会删除 `mkc-dev` 和 `ingress-nginx` 命名空间，但保留 Docker Desktop Kubernetes 集群本身。

## Secret 管理

本地使用 `envsubst` 将 `infra/k8s/*/secret.yaml.tpl` 渲染为 `secret.yaml`：

```bash
export MYSQL_ROOT_PASSWORD=dev-root
export MYSQL_PASSWORD=dev-mkc
export REDIS_PASSWORD=dev-redis
export MINIO_ROOT_PASSWORD=dev-minio
./infra/scripts/render-secrets.sh
```

渲染后的 `secret.yaml` 已加入 `.gitignore`，**严禁提交到 Git**。

## 常用命令

```bash
# 查看所有 Pod
kubectl get pods -n mkc-dev

# 查看服务
kubectl get svc -n mkc-dev

# 查看 PVC
kubectl get pvc -n mkc-dev

# 查看 Ingress
kubectl get ingress -n mkc-dev

# 查看 MySQL 日志
kubectl logs -f deployment/mysql -n mkc-dev

# 进入 MySQL 容器
kubectl exec -it deployment/mysql -n mkc-dev -- mysql -u root -p
```

## 故障排查

| 症状 | 可能原因 | 排查命令 |
|---|---|---|
| Pod Pending | PVC 未绑定 | `kubectl get pvc -n mkc-dev` |
| Pod CrashLoopBackOff | 密码错误或配置错误 | `kubectl logs <pod> -n mkc-dev` |
| Ingress 无法访问 | Ingress Controller 未就绪 | `kubectl get pods -n ingress-nginx` |
| 本地 DNS 不生效 | `/etc/hosts` 未配置 | 检查 hosts 文件 |

## 注意事项

- `infra/k8s/gateway/deployment.yaml` 不在 S0-2 范围内，Gateway 应用镜像将在 S0-7 构建后补充。
- cert-manager 本地开发暂不启用，生产环境必需。
- 本地环境以“能跑通”为首要目标，不追求高可用。
