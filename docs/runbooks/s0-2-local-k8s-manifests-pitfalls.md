# MKC 项目 S0-2 踩坑实录：本地 K8s 开发环境搭建与 manifests 编写

> 项目：MKC（Multimedia Knowledge Companion）
> 阶段：S0-2 本地 K8s 开发环境与 manifests
> 时间：2026-07-07
> 目标读者：想用 Docker Desktop + kubectl 在本地跑通一套中间件栈的开发者

---

## 一、S0-2 到底做了什么

S0-2 的目标是在本地搭一套与生产架构一致的 Kubernetes 开发环境，并把所有依赖服务的 manifests 写成文件，最终做到 `infra/scripts/local-up.sh` 一键拉起。

最终交付物包括：

| 模块 | 内容 |
|------|------|
| nginx-ingress | 自包含 manifest（无 admission webhook），本地 Ingress 入口 |
| MySQL 8.0 | StatefulSet + ConfigMap + Secret + PVC |
| Redis 7.2 | Deployment + ConfigMap + Secret + PVC |
| MinIO | Deployment + Secret + PVC + 初始化 Bucket Job |
| Milvus 2.4.1 | standalone Deployment + 独立 etcd Deployment |
| Jaeger 1.57 | all-in-one Deployment |
| Gateway | Service + Ingress（Deployment 留到 S0-7）|
| 脚本 | `local-up.sh`、`local-down.sh`、`port-forward.sh`、`render-secrets.sh` |
| 文档 | `infra/README.md` 部署说明与依赖版本表 |

检查清单全部完成，PR #3 已成功合并到 main。

---

## 二、踩坑清单与解决方案

### 坑 1：macOS 没有 `envsubst`

**现象：**
```bash
./infra/scripts/render-secrets.sh
# envsubst: command not found
```

**原因：** macOS 默认不带 gettext 工具包，`envsubst` 需要 `brew install gettext`。

**解决：** 在 `render-secrets.sh` 里加 Python fallback，优先用 `envsubst`，没有就用 Python 的 `os.path.expandvars`。

```bash
if command -v envsubst >/dev/null 2>&1; then
  envsubst < "$f" > "$target"
else
  python3 -c 'import os, sys; sys.stdout.write(os.path.expandvars(sys.stdin.read()))' < "$f" > "$target"
fi
```

**经验：** 脚本不要假设用户的 mac 已经装了 GNU 工具链，给一个零依赖的 fallback，第一次运行就能通过。

---

### 坑 2：ingress-nginx 镜像从 `registry.k8s.io` 拉不下来

**现象：**
```
Failed to pull image "registry.k8s.io/ingress-nginx/controller:v1.10.1"
```

**原因：** 当前网络环境访问 `registry.k8s.io` 不稳定，镜像拉取超时。

**解决：** 切换到 DaoCloud 国内镜像源。

```yaml
image: m.daocloud.io/registry.k8s.io/ingress-nginx/controller:v1.10.1
```

**经验：** 本地开发先用国内镜像源跑通，后面生产环境再通过镜像仓库同步或替换地址。

---

### 坑 3：Docker Hub / Quay 的镜像也拉不下来

**现象：** MySQL、Redis、MinIO、Milvus、etcd、Jaeger 全部 `ImagePullBackOff`。

**原因：** Docker Hub 和 Quay 同样受网络环境影响。

**解决：** 统一替换为 DaoCloud 镜像前缀。

```yaml
# Docker Hub
image: docker.m.daocloud.io/library/mysql:8.0.37
image: docker.m.daocloud.io/library/redis:7.2-alpine
image: docker.m.daocloud.io/minio/minio:RELEASE.2024-05-10T01-41-38Z
image: docker.m.daocloud.io/milvusdb/milvus:v2.4.1
image: docker.m.daocloud.io/jaegertracing/all-in-one:1.57

# Quay
image: quay.m.daocloud.io/coreos/etcd:v3.5.14
```

**经验：** 做本地 K8s 栈时，先把所有镜像地址列一张表，统一换源，避免逐个排查。

---

### 坑 4：ingress-nginx controller 因为 `runAsNonRoot` 起不来

**现象：**
```
Error: container has runAsNonRoot and image has non-numeric user (www-data)
```

**原因：** 精简后的 manifest 没有指定 numeric user，Kubernetes 拒绝启动。

**解决：** 给 controller 容器加上 `runAsUser: 101`。

```yaml
securityContext:
  allowPrivilegeEscalation: false
  runAsNonRoot: true
  runAsUser: 101
  capabilities:
    drop: ["ALL"]
    add: ["NET_BIND_SERVICE"]
```

**经验：** 使用非 root 镜像时，安全上下文里最好显式指定 numeric UID，否则不同 K8s 发行版行为不一致。

---

### 坑 5：`readOnlyRootFilesystem: true` 导致 controller 写不了 fake cert

**现象：** controller 启动后反复重启，日志里有 fake certificate 写入失败。

**原因：** ingress-nginx 本地运行时会写临时证书到根文件系统。

**解决：** 去掉 `readOnlyRootFilesystem: true`。

```yaml
securityContext:
  allowPrivilegeEscalation: false
  runAsNonRoot: true
  runAsUser: 101
  capabilities:
    drop: ["ALL"]
    add: ["NET_BIND_SERVICE"]
  # readOnlyRootFilesystem: true  # 本地开发先关闭
```

**经验：** 生产 manifest 里再开启只读根文件系统，并配合 emptyDir 写临时文件；本地先以跑通为主。

---

### 坑 6：RBAC 权限不够

**现象：** controller 日志里不断报 forbidden。

```
endpointslices.discovery.k8s.io is forbidden
leases.coordination.k8s.io is forbidden
events is forbidden
```

**原因：** 自包含 manifest 的 ClusterRole 规则比官方 Helm  chart 精简，漏了这几项资源。

**解决：** 补充 ClusterRole。

```yaml
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  verbs: ["get", "list", "watch", "create", "update"]
- apiGroups: [""]
  resources: ["events"]
  verbs: ["create", "patch"]
- apiGroups: ["discovery.k8s.io"]
  resources: ["endpointslices"]
  verbs: ["get", "list", "watch"]
```

**经验：** 从官方 manifest 精简时，RBAC 不要过度删减；可以先给宽权限跑通，再按最小权限收紧。

---

### 坑 7：readiness probe `/readyz` 返回 404

**现象：** controller pod 一直不 Ready。

```
HTTP probe failed with statuscode: 404
path: /readyz
```

**原因：** 这个精简版 controller 没有启用 admission webhook，`/readyz` 路径不存在。

**解决：** 把 liveness/readiness 路径都改成 `/healthz`（controller 的 metrics 端口 10254 上提供）。

```yaml
readinessProbe:
  httpGet:
    path: /healthz
    port: 10254
    scheme: HTTP
```

**经验：** 复制官方 manifest 时，要核对探针路径是否和当前启动参数一致；关闭 webhook 后很多默认路径会消失。

---

### 坑 8：Docker Desktop 不支持 `kubectl run` 的 attach/exec

**现象：** 用 `kubectl run --rm -i` 创建 minio client pod 创建 Milvus bucket 时报错。

```
error sending request: Post "//[::]:58027/cri/attach/..."
http: server gave HTTP response to HTTPS client
```

**原因：** Docker Desktop 的 CRI 实现不支持这种 attach/exec 请求。

**解决：** 不再用交互式 `kubectl run`，而是写一个 Job：`infra/k8s/minio/init-buckets-job.yaml`。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: minio-init-buckets
spec:
  template:
    spec:
      restartPolicy: OnFailure
      initContainers:
        - name: wait-for-minio
          image: docker.m.daocloud.io/library/busybox:1.36
          command:
            - sh
            - -c
            - |
              until wget -qO- http://minio:9000/minio/health/ready; do
                echo "Waiting for MinIO..."
                sleep 2
              done
      containers:
        - name: mc
          image: docker.m.daocloud.io/minio/mc:latest
          command:
            - /bin/sh
            - -c
            - |
              mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
              mc mb -p local/a-bucket
              mc mb -p local/mkc-uploads
              mc mb -p local/mkc-outputs
              mc version enable local/mkc-uploads
              mc version enable local/mkc-outputs
```

然后在 `local-up.sh` 里等待 Job 完成：

```bash
kubectl wait --for=condition=complete job/minio-init-buckets -n "$NAMESPACE" --timeout=300s
```

**经验：** 在 Docker Desktop 上尽量用 Job/CronJob/日志流，而不是依赖 `kubectl exec` 或 `kubectl run -i`。

---

### 坑 9：Milvus  CrashLoopBackOff，日志堆栈显示在解析 DNS

**现象：**
```
milvus-xxx 0/1 CrashLoopBackOff
```

看日志最后是一大堆 `net.dnsPacketRoundTrip` 的 goroutine 堆栈，很容易误以为是 DNS 问题。

**真正原因：** 一开始用了一个自定义的 `milvus.yaml` ConfigMap，里面只写了 etcd、minio、messageQueue、queryNode cache 等少量配置。挂载这个文件后，Milvus 丢失了大量默认组件端口配置，导致 rootCoord 和 proxy 都尝试监听 `19530`，触发 `bind: address already in use` 后 panic。

**解决：** 不挂载自定义 `milvus.yaml`，改用环境变量注入必要配置。

```yaml
env:
  - name: ETCD_ENDPOINTS
    value: "milvus-etcd:2379"
  - name: MINIO_ADDRESS
    value: "minio:9000"
  - name: MINIO_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: minio-secret
        key: root-user
  - name: MINIO_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: minio-secret
        key: root-password
  - name: MINIO_USE_SSL
    value: "false"
```

bucket 使用 Milvus 默认的 `a-bucket`，并在 MinIO 初始化 Job 里一起创建。

**经验：**
1. 不要被 goroutine 堆栈的最后几行误导，往上看真正的 panic 信息。
2. 如果要覆盖 Milvus 配置，最好基于完整默认配置修改；否则优先用官方支持的环境变量。
3. 组件端口冲突这种错误在 standalone 模式下尤其隐蔽，因为所有组件跑在一个进程里。

---

## 三、S0-2 的目录结构速览

```
infra/
├── README.md
├── scripts/
│   ├── local-up.sh
│   ├── local-down.sh
│   ├── port-forward.sh
│   └── render-secrets.sh
└── k8s/
    ├── namespaces/mkc-dev.yaml
    ├── nginx-ingress/ingress-nginx.yaml
    ├── mysql/
    ├── redis/
    ├── minio/
    ├── milvus/
    ├── jaeger/
    └── gateway/
```

这种按**服务/组件**组织 manifests 的方式，比按资源类型（deployment/ service/ configmap）拆分更适合本地开发：每个目录就是一个可以单独 `kubectl apply -f` 的最小单元。

---

## 四、给后来者的建议

1. **先换镜像源，再排应用错。** 本地 K8s 环境 80% 的启动问题都是镜像拉不下来，先把所有镜像源统一处理。
2. **用 Job 代替交互式命令。** 在 Docker Desktop 上，`kubectl run -i` 和 `kubectl exec` 经常受限，可观测的 Job 更稳定。
3. **覆盖默认配置要小心。** 挂载整个配置文件会覆盖所有默认值，优先使用环境变量，或者基于完整默认配置修改。
4. **日志要从上往下看。** Go panic 的最后往往是大量 goroutine 堆栈，真正的原因通常在日志前半段。
5. **脚本要有 fallback。** 不要假设每个开发者都装了 `envsubst`、`gettext` 或特定版本的 CLI 工具。
6. **本地 Ingress 用 `/etc/hosts`。** 搭配 nginx-ingress 的 LoadBalancer Service，在 `/etc/hosts` 里配 `127.0.0.1 mkc.local` 就能直接访问。

---

## 五、下一步

S0-2 已经合进 main，接下来进入 S0-3：GitHub Actions CI 流水线完善。目标是把本地能跑通的环境和测试，通过 CI 在每个 PR 上自动验证。

---

*本文由 Claude Code 协助整理，基于 MKC 项目 S0-2 真实踩坑记录。*
