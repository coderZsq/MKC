# 技术文档：[S0-2] 本地 Kubernetes 开发环境与基础设施部署架构

> 版本：v1.0  
> 日期：2026-07-06  > 作者：朱双泉  > 级别：架构师/平台负责人  > 关联 PRD：[PRD_S0-2_local_k8s_manifests.md](./PRD_S0-2_local_k8s_manifests.md)

---

## 1. 文档目标

本文档详细描述 MKC 项目在本地开发环境中所需的 Kubernetes 基础设施架构，包括集群选型、网络规划、存储设计、各组件部署细节、Secret 管理策略、本地 DNS 解析、调试方法以及向生产环境迁移的路径。

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                      开发者本地机器                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Docker Desktop Kubernetes               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐   │   │
│  │  │  nginx-     │  │  cert-      │  │  Gateway  │   │   │
│  │  │  ingress    │  │  manager    │  │  (Gin)    │   │   │
│  │  │  controller │  │             │  │           │   │   │
│  │  └──────┬──────┘  └─────────────┘  └─────┬─────┘   │   │
│  │         │                                  │         │   │
│  │  ┌──────┴──────────────────────────────────┘         │   │
│  │  │              mkc-dev namespace                     │   │
│  │  │  ┌────────┐ ┌───────┐ ┌───────┐ ┌────────┐      │   │
│  │  │  │ MySQL  │ │ Redis │ │ MinIO │ │ Milvus │      │   │
│  │  │  │ (PVC)  │ │ (PVC) │ │ (PVC) │ │        │      │   │
│  │  │  └────────┘ └───────┘ └───────┘ └────────┘      │   │
│  │  │  ┌────────┐ ┌─────────────┐ ┌────────┐          │   │
│  │  │  │ Jaeger │ │ AI Service  │ │ Client │          │   │
│  │  │  │        │ │ (Flask +    │ │ (Web)  │          │   │
│  │  │  │        │ │  Celery)    │ │        │          │   │
│  │  │  └────────┘ └─────────────┘ └────────┘          │   │
│  │  └──────────────────────────────────────────────────┘   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 本地集群选型

### 3.1 方案说明

本地开发使用 **Docker Desktop 内置 Kubernetes**，无需额外安装 minikube/k3d/kind。该方案的优势：

- 与 Docker Desktop 共用 Docker Daemon，镜像构建后可直接被 K8s 使用
- 无需额外的虚拟机或容器化集群层，链路更短
- 适合 macOS/Windows 开发者日常开发

### 3.2 启用步骤

Docker Desktop → Settings → Kubernetes → **Enable Kubernetes** → Apply & Restart

验证集群就绪：
```bash
kubectl get nodes
kubectl get ns
```

### 3.3 资源配置

Docker Desktop → Settings → Resources：

| 配置项 | 最低 | 推荐 |
|---|---|---|
| CPU | 4 核 | 6 核 |
| Memory | 8 GB | 12 GB |
| Disk | 30 GB | 50 GB |

**说明**：Milvus + MySQL + Redis + MinIO + AI Service 同时运行较占内存，建议 12GB 以上。

---

## 4. 命名空间与网络规划

### 4.1 命名空间

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mkc-dev
  labels:
    app.kubernetes.io/part-of: mkc
    environment: dev
```

### 4.2 网络访问路径

| 访问目标 | 本地地址 | 说明 |
|---|---|---|
| Gateway API | http://mkc.local/api/v1/ | 通过 Ingress |
| Swagger UI | http://mkc.local/swagger/index.html | 通过 Ingress |
| MinIO Console | http://minio.mkc.local | 通过 Ingress |
| Jaeger UI | http://jaeger.mkc.local | 通过 Ingress |
| Milvus | cluster internal | 仅内部访问 |

### 4.3 本地 DNS 配置

修改 `/etc/hosts`：
```
127.0.0.1 mkc.local
127.0.0.1 minio.mkc.local
127.0.0.1 jaeger.mkc.local
127.0.0.1 api.mkc.local
```

或使用 [nip.io](https://nip.io)：
```
127-0-0-1.nip.io
```

---

## 5. 存储设计

### 5.1 StorageClass

Docker Desktop Kubernetes 默认提供 `hostpath` provisioner，可直接创建 PVC 并自动绑定。

```bash
kubectl get storageclass
```

预期输出类似：
```
NAME                 PROVISIONER          RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION   AGE
hostpath (default)   docker.io/hostpath   Delete          Immediate           true                   1h
```

### 5.2 PVC 策略

| 服务 | 容量 | 访问模式 | 说明 |
|---|---|---|---|
| MySQL | 10Gi | ReadWriteOnce | 业务数据持久化 |
| Redis | 5Gi | ReadWriteOnce | AOF 持久化 |
| MinIO | 20Gi | ReadWriteOnce | 对象存储数据 |

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-data
  namespace: mkc-dev
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

---

## 6. 组件部署详情

### 6.1 nginx-ingress-controller

Docker Desktop K8s 默认不自带 Ingress Controller，需手动安装官方 nginx-ingress。

**部署方式**：官方 manifest

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/cloud/deploy.yaml
```

**验证就绪**：
```bash
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

**本地关键配置**：
- Docker Desktop 会自动将 Ingress Controller 的 Service 通过 `localhost` 暴露 80/443
- 无需额外 NodePort 或 hostNetwork 配置

**Ingress 示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
  namespace: mkc-dev
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  ingressClassName: nginx
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

**上传大文件配置**：
```yaml
annotations:
  nginx.ingress.kubernetes.io/proxy-body-size: "500m"
  nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
  nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
```

### 6.2 cert-manager

本地开发环境可暂不启用，生产环境必需。

```bash
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

生产 ClusterIssuer 示例：
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

### 6.3 MySQL

**部署方式**：StatefulSet + Headless Service + PVC

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: mkc-dev
spec:
  serviceName: mysql
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
        - name: mysql
          image: mysql:8.0.37
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: root-password
            - name: MYSQL_DATABASE
              value: mkc
            - name: MYSQL_USER
              value: mkc
            - name: MYSQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
          ports:
            - containerPort: 3306
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

**字符集配置**（ConfigMap）：
```ini
[mysqld]
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
default-time-zone='+08:00'
max_connections=200
```

### 6.4 Redis

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: mkc-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7.2-alpine
          command:
            - redis-server
            - /etc/redis/redis.conf
          ports:
            - containerPort: 6379
          volumeMounts:
            - name: data
              mountPath: /data
            - name: config
              mountPath: /etc/redis
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: redis-data
        - name: config
          configMap:
            name: redis-config
```

**redis.conf**：
```
appendonly yes
appendfsync everysec
maxmemory 128mb
maxmemory-policy allkeys-lru
```

### 6.5 MinIO

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: mkc-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: minio/minio:RELEASE.2024-05-10T01-41-38Z
          command:
            - minio
            - server
            - /data
            - --console-address
            - ":9001"
          env:
            - name: MINIO_ROOT_USER
              value: "mkc"
            - name: MINIO_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: minio-secret
                  key: root-password
          ports:
            - containerPort: 9000
            - containerPort: 9001
          volumeMounts:
            - name: data
              mountPath: /data
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "300m"
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-data
```

**初始化 Bucket Job**：
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: minio-init-buckets
  namespace: mkc-dev
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: mc
          image: minio/mc:latest
          command:
            - /bin/sh
            - -c
            - |
              mc alias set local http://minio:9000 mkc $MINIO_ROOT_PASSWORD
              mc mb -p local/mkc-uploads
              mc mb -p local/mkc-outputs
              mc policy set public local/mkc-uploads
```

### 6.6 Milvus

本地使用 standalone 模式，通过 Helm 部署：

```bash
helm repo add milvus https://milvus-io.github.io/milvus-helm/
helm install milvus milvus/milvus \
  --namespace mkc-dev \
  --set cluster.enabled=false \
  --set etcd.replicaCount=1 \
  --set minio.mode=standalone \
  --set pulsar.enabled=false
```

**资源占用控制**：
```yaml
milvus:
  standalone:
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "1000m"
```

### 6.7 Jaeger

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: mkc-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
        - name: jaeger
          image: jaegertracing/all-in-one:1.57
          ports:
            - containerPort: 16686  # UI
            - containerPort: 4317   # OTLP gRPC
            - containerPort: 4318   # OTLP HTTP
          env:
            - name: COLLECTOR_OTLP_ENABLED
              value: "true"
```

---

## 7. Secret 管理策略

### 7.1 本地开发

使用 Kubernetes Secret，密码通过 `envsubst` 注入：

```bash
export MYSQL_ROOT_PASSWORD=dev-root-pass
export MYSQL_PASSWORD=dev-pass
export MINIO_ROOT_PASSWORD=dev-minio-pass

envsubst < infra/k8s/mysql/secret.yaml.tpl > infra/k8s/mysql/secret.yaml
kubectl apply -f infra/k8s/mysql/secret.yaml
```

### 7.2 Secret 模板示例

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: mkc-dev
type: Opaque
stringData:
  root-password: "${MYSQL_ROOT_PASSWORD}"
  password: "${MYSQL_PASSWORD}"
```

### 7.3 生产环境

使用 **External Secrets Operator** 或云厂商 Secret Manager：
- AWS: AWS Secrets Manager + IRSA
- 阿里云: KMS + ACK Secret 集成
- 通用: External Secrets Operator + HashiCorp Vault

**底线**：真实密码永不提交 Git。

---

## 8. 部署脚本

### 8.1 local-up.sh

```bash
#!/bin/bash
set -e

NAMESPACE="mkc-dev"

echo "Checking Docker Desktop Kubernetes..."
if ! kubectl get nodes >/dev/null 2>&1; then
  echo "Error: Docker Desktop Kubernetes is not enabled or kubectl cannot connect."
  echo "Please enable Kubernetes in Docker Desktop settings."
  exit 1
fi

echo "Installing ingress-nginx..."
kubectl apply -f infra/k8s/nginx-ingress/ingress-nginx.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

echo "Creating namespace..."
kubectl apply -f infra/k8s/namespaces/mkc-dev.yaml

echo "Rendering secrets..."
./infra/scripts/render-secrets.sh

echo "Applying manifests..."
kubectl apply -f infra/k8s/mysql/
kubectl apply -f infra/k8s/redis/
kubectl apply -f infra/k8s/minio/
kubectl apply -f infra/k8s/milvus/
kubectl apply -f infra/k8s/jaeger/

echo "Waiting for pods..."
kubectl wait --for=condition=ready pod -l app=mysql -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n "$NAMESPACE" --timeout=300s

echo "Done! Add the following lines to /etc/hosts:"
echo "127.0.0.1 mkc.local"
echo "127.0.0.1 minio.mkc.local"
echo "127.0.0.1 jaeger.mkc.local"
```

### 8.2 local-down.sh

```bash
#!/bin/bash
set -e

NAMESPACE="mkc-dev"

echo "Deleting namespace resources..."
kubectl delete namespace "$NAMESPACE" --ignore-not-found=true

echo "Note: Docker Desktop Kubernetes cluster itself is kept running."
echo "To fully disable, use Docker Desktop settings."
```

### 8.3 render-secrets.sh

```bash
#!/bin/bash
set -e

export MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-dev-root}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-dev-mkc}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-dev-minio}"

for f in infra/k8s/*/secret.yaml.tpl; do
  target="${f%.tpl}"
  envsubst < "$f" > "$target"
done
```

### 8.4 本地镜像加载

Docker Desktop K8s 直接使用本地 Docker 镜像，无需额外导入：

```bash
cd gateway
docker build -t mkc-gateway:latest .

cd ../ai-service
docker build -t mkc-ai-service:latest .
```

部署时使用 `imagePullPolicy: IfNotPresent` 即可使用本地镜像：

```yaml
spec:
  template:
    spec:
      containers:
        - name: gateway
          image: mkc-gateway:latest
          imagePullPolicy: IfNotPresent
```

---

## 9. 调试与端口转发

### 9.1 常用命令

```bash
# 查看所有 Pod
kubectl get pods -n mkc-dev

# 查看日志
kubectl logs -f deployment/mysql -n mkc-dev

# 进入容器
kubectl exec -it deployment/mysql -n mkc-dev -- mysql -u root -p

# 端口转发（本地调试）
kubectl port-forward -n mkc-dev svc/mysql 3306:3306
kubectl port-forward -n mkc-dev svc/redis 6379:6379
kubectl port-forward -n mkc-dev svc/minio 9000:9000 9001:9001
```

### 9.2 问题排查清单

| 症状 | 可能原因 | 排查命令 |
|---|---|---|
| Pod Pending | PVC 未绑定 | `kubectl get pvc -n mkc-dev` |
| Pod CrashLoopBackOff | 密码错误或配置错误 | `kubectl logs ...` |
| Ingress 无法访问 | Ingress Controller 未就绪 | `kubectl get pods -n ingress-nginx` |
| 本地 DNS 不生效 | /etc/hosts 未配置 | 检查 hosts 文件 |

---

## 10. 向生产环境迁移

| 组件 | 本地（Docker Desktop K8s） | 生产 |
|---|---|---|
| K8s 集群 | Docker Desktop 内置 | 云厂商托管 K8s |
| Ingress | nginx-ingress | 云厂商 LB + nginx-ingress |
| TLS | 自签/跳过 | cert-manager + Let's Encrypt |
| MySQL | 单节点 StatefulSet | 云数据库 RDS / 主从集群 |
| Redis | 单节点 | 云 Redis / Sentinel / Cluster |
| MinIO | 单节点 | 云对象存储 S3/OSS |
| Milvus | standalone | cluster 模式 |
| Secret | K8s Secret | External Secrets / Vault |

---

## 11. 检查清单

- [ ] Docker Desktop Kubernetes 已启用
- [ ] kubectl 能正常连接 Docker Desktop K8s
- [ ] nginx-ingress-controller Running
- [ ] MySQL/Redis/MinIO/Milvus/Jaeger 全部 Running
- [ ] `kubectl apply -f infra/k8s/` 可一键应用
- [ ] `/etc/hosts` 配置完成
- [ ] `local-up.sh` 和 `local-down.sh` 可正常工作
- [ ] 本地构建的镜像可被 K8s 直接使用
- [ ] Secret 未提交到 Git
