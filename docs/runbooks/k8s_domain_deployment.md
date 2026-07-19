# Kubernetes Domain Deployment Runbook

This runbook covers the S5-8 demo/production deployment path for MKC.

## Scope

- Gateway, AI Service, Celery worker, Flutter Web client.
- MySQL, Redis, MinIO, Milvus, and Milvus etcd.
- Ingress NGINX with HTTPS through cert-manager.
- Static manifest validation, deployment, smoke test, upgrade, rollback, and triage.

## Prerequisites

- Kubernetes 1.28 or newer.
- `kubectl` connected to the target cluster.
- Ingress NGINX installed and using `ingressClassName: nginx`.
- cert-manager installed for the `prod` overlay.
- DNS `A` or `CNAME` record for the demo domain pointing to the ingress load balancer.
- Images pushed for Gateway, AI Service, and Client.

## Configuration Files

| Purpose | Path |
|---|---|
| Kustomize base | `infra/k8s/base` |
| Local overlay | `infra/k8s/overlays/local` |
| Production overlay | `infra/k8s/overlays/prod` |
| Secret placeholders | `infra/k8s/overlays/prod/secrets.env.example` |
| Deploy helper | `scripts/deploy_k8s.sh` |
| Smoke test | `scripts/smoke_prod.sh` |

## Prepare Production Overlay

1. Copy `infra/k8s/overlays/prod/secrets.env.example` to a private file outside Git or inject equivalent values from a secret manager.
2. Replace `MKC_DOMAIN` in `infra/k8s/overlays/prod/kustomization.yaml`.
3. Replace `ops@example.com` in `infra/k8s/overlays/prod/cluster-issuer.yaml`.
4. Replace image tags in `infra/k8s/overlays/prod/kustomization.yaml` with immutable release tags.
5. Choose model providers. The checked-in overlay defaults to `mock` providers so manifests can render without external API keys.

Never commit real values for JWT secrets, database passwords, provider API keys, or TLS private keys.

## Validate Manifests

```bash
kubectl kustomize infra/k8s/overlays/local >/tmp/mkc-local.yaml
kubectl kustomize infra/k8s/overlays/prod >/tmp/mkc-prod.yaml
```

Optional schema validation:

```bash
kubeconform -strict -summary /tmp/mkc-prod.yaml
```

## Deploy

```bash
./scripts/deploy_k8s.sh prod
```

Manual equivalent:

```bash
kubectl apply -k infra/k8s/overlays/prod
kubectl rollout status deployment/gateway -n mkc --timeout=300s
kubectl rollout status deployment/ai-service -n mkc --timeout=300s
kubectl rollout status deployment/client -n mkc --timeout=300s
```

## Smoke Test

```bash
BASE_URL=https://mkc.example.com \
NAMESPACE=mkc \
./scripts/smoke_prod.sh
```

To include upload:

```bash
BASE_URL=https://mkc.example.com \
UPLOAD_FILE=/path/to/smoke.pdf \
./scripts/smoke_prod.sh
```

The smoke test checks:

- Gateway `/api/v1/health`.
- Client static entrypoint.
- Register and login.
- Optional upload.
- Authenticated task list.
- AI Service internal health from inside the cluster.

## Upgrade

1. Build and push new images.
1. Update image tags in the prod overlay.
1. Render and review the diff:

```bash
kubectl kustomize infra/k8s/overlays/prod >/tmp/mkc-prod.yaml
```

1. Apply and wait for rollouts:

```bash
./scripts/deploy_k8s.sh prod
```

1. Run smoke test.

## Rollback

Use Kubernetes rollout history for stateless app services:

```bash
kubectl rollout history deployment/gateway -n mkc
kubectl rollout undo deployment/gateway -n mkc
kubectl rollout undo deployment/ai-service -n mkc
kubectl rollout undo deployment/client -n mkc
kubectl rollout status deployment/gateway -n mkc --timeout=300s
```

For data migrations, restore from the database/object-storage backup matching the release window before rolling back application images.

## Persistence

| Component | Persistence |
|---|---|
| MySQL | StatefulSet `volumeClaimTemplates` at `/var/lib/mysql` |
| Redis | StatefulSet `volumeClaimTemplates` at `/data` with AOF |
| MinIO | PVC `minio-data` mounted at `/data` |
| Milvus etcd | StatefulSet `volumeClaimTemplates` at `/etcd-data` |
| Milvus | StatefulSet `volumeClaimTemplates` at `/var/lib/milvus` |

PVCs are not deleted by normal pod restarts. Before deleting a namespace, confirm backups exist.

## DNS and TLS Triage

```bash
kubectl get ingress -n mkc
kubectl describe ingress mkc-ingress -n mkc
kubectl get certificate -n mkc
kubectl describe certificate mkc-tls -n mkc
kubectl describe clusterissuer letsencrypt-prod
```

Common issues:

- DNS points to the wrong load balancer.
- HTTP-01 challenge cannot reach ingress on port 80.
- `cert-manager.io/cluster-issuer` annotation does not match an installed issuer.
- Domain in `spec.tls.hosts` does not match `spec.rules.host`.

## SSE and Upload Triage

Ingress annotations required for MKC:

- `nginx.ingress.kubernetes.io/proxy-buffering: "off"`
- `nginx.ingress.kubernetes.io/proxy-read-timeout: "600"`
- `nginx.ingress.kubernetes.io/proxy-send-timeout: "600"`
- `nginx.ingress.kubernetes.io/proxy-body-size: "500m"`

If SSE stalls, test directly through port-forwarding:

```bash
kubectl port-forward svc/gateway -n mkc 8080:8080
curl -N http://localhost:8080/api/v1/health
```

If uploads fail with 413, align browser, Gateway, ingress, and object storage limits.

## Internal Exposure Check

Only `mkc-ingress` should expose public traffic. Internal services should remain `ClusterIP`.

```bash
kubectl get svc -n mkc
kubectl get ingress -n mkc
```

Do not add public ingress for AI Service, Redis, MySQL, MinIO S3, Milvus, `/metrics`, or tracing endpoints.
