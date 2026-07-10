# MKC 运维排错手册

## 本地 K8s 排查

详见 [TECH_S0-2_local_k8s_manifests.md](./tech/TECH_S0-2_local_k8s_manifests.md) 第 9 节。

## 常用命令

```bash
kubectl get pods -n mkc-dev
kubectl logs -f deployment/gateway -n mkc-dev
kubectl exec -it deployment/mysql -n mkc-dev -- mysql -u root -p
```

## ASR 上传与转写链路排错

详见 [ASR 上传与转写链路排错手册](./asr-upload-pipeline-debug.md)。
