# MKC Infrastructure

本地与生产基础设施配置，基于 Kubernetes。

## 目录结构

```
infra/
├── k8s/              # Kubernetes manifests
│   ├── namespaces/
│   ├── nginx-ingress/
│   ├── cert-manager/
│   ├── mysql/
│   ├── redis/
│   ├── minio/
│   ├── milvus/
│   ├── jaeger/
│   ├── gateway/
│   └── ai-service/
└── scripts/          # 本地部署脚本
    ├── local-up.sh
    ├── local-down.sh
    ├── port-forward.sh
    └── render-secrets.sh
```

## 本地启动

```bash
./infra/scripts/local-up.sh
```

## 本地关闭

```bash
./infra/scripts/local-down.sh
```

## 端口转发

```bash
./infra/scripts/port-forward.sh
```
