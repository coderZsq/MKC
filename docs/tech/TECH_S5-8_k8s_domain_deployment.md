# 技术文档：[S5-8] 部署到 Kubernetes 集群并绑定域名

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：后端/DevOps 工程师
> 关联 PRD：[../prd/PRD_S5-8_k8s_domain_deployment.md](../prd/PRD_S5-8_k8s_domain_deployment.md)

---

## 1. 文档目标

定义生产或演示环境 Kubernetes 部署方案，包括 manifests/overlay、Ingress、TLS、Secret、持久化、健康检查、发布与回滚。

---

## 2. 技术栈

- Kubernetes 1.28+
- Kustomize / Helm
- Ingress NGINX
- Cert-Manager
- MySQL, Redis, MinIO, Milvus
- Docker images

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `https://<domain>/` | 无 | Flutter Web |
| GET | `https://<domain>/api/v1/healthz` | 无 | Gateway 健康检查 |
| GET | `http://ai-service:8000/healthz` | 集群内 | AI Service 健康检查 |

---

## 4. 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts: ["mkc.example.com"]
      secretName: mkc-tls
```

Secret 只提交模板：

```text
JWT_SECRET=
MYSQL_DSN=
ZHIPU_API_KEY=
KIMI_API_KEY=
```

---

## 5. 模块设计

- `base`：通用 Deployment、Service、ConfigMap。
- `overlays/local`：本地集群配置。
- `overlays/prod`：域名、TLS、资源配额、镜像 tag。
- `smoke_prod.sh`：部署后主链路检查。
- runbook：DNS、证书、Ingress、Pod、日志排障。

---

## 6. 关键代码实现

```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
livenessProbe:
  httpGet:
    path: /healthz
    port: http
```

```bash
kubectl apply -k infra/k8s/overlays/prod
kubectl rollout status deploy/mkc-gateway -n mkc
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| Ingress 未路由 | 404 | DEPLOY_INGRESS_NOT_FOUND | Ingress 路由未生效 |
| 证书签发失败 | N/A | DEPLOY_CERT_FAILED | TLS 证书签发失败 |
| Pod 未就绪 | N/A | DEPLOY_POD_NOT_READY | 服务未就绪 |
| Secret 缺失 | N/A | DEPLOY_SECRET_MISSING | 部署缺少必要 Secret |

---

## 8. Web 端适配要点

Flutter Web 构建需注入 API base URL，Ingress 需支持 SSE 长连接、上传大小限制和静态资源缓存。

---

## 9. 测试策略

- 静态测试：`kubectl kustomize`、kubeconform/kubeval。
- 集成测试：部署到测试 namespace 并执行 health smoke。
- E2E：在线 Demo 登录、上传、问答、引用查看。

---

## 10. 检查清单

- [ ] 关键文件已实现
- [ ] smoke test 通过
- [ ] 部署文档同步更新
